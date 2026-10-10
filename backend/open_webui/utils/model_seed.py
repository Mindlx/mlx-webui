"""Seed bundled SentenceTransformer models into the runtime cache directory.

The Docker image bakes the default RAG/auxiliary embedding models into
``SENTENCE_TRANSFORMERS_HOME`` (``/app/backend/data/cache/embedding/models``)
at build time. However, deployments that bind-mount a host directory over
``/app/backend/data`` (e.g. ``docker run -v "$PWD/data:/app/backend/data"``)
hide those baked-in files: a fresh bind mount is empty, so the bundled models
are masked and the app silently falls back to downloading them at first use
(which may fail on offline/restricted networks).

To keep the bundled models usable regardless of mount layout, the build also
copies them to a staging directory *outside* the mounted tree
(``BUNDLED_MODELS_DIR``, default ``/opt/open-webui/embedding_models``). On
startup this module seeds them into ``SENTENCE_TRANSFORMERS_HOME`` if (and
only if) that target is missing them, so out-of-the-box local embeddings work
on a standard deployment.

Seeding is crash-safe: each model is copied to a temporary sibling directory
and atomically renamed into place, so an interrupted seed never leaves a
partial snapshot visible. A pre-existing but incomplete snapshot (e.g. left by
an older build or an interrupted copy) is detected and re-seeded instead of
being skipped.
"""

import logging
import os
import shutil

log = logging.getLogger(__name__)

# Path baked at image build time, deliberately outside /app/backend/data so a
# bind mount over the data volume can never hide it. Overridable via env for
# non-Docker/local installs.
BUNDLED_MODELS_DIR = os.getenv('BUNDLED_MODELS_DIR', '/opt/open-webui/embedding_models')

# Filenames whose presence inside a snapshot indicates the weights were fully
# copied. A seed that was killed mid-copy leaves ``snapshots/<commit>/`` present
# but without any of these, which must not be treated as "already seeded".
_WEIGHT_FILES = ('model.safetensors', 'pytorch_model.bin', 'model.bin', 'tf_model.h5')


def _is_snapshot_complete(model_dir: str) -> bool:
    """Return True if a HuggingFace cache dir holds at least one real snapshot.

    A cache dir looks like ``<name>/snapshots/<commit>/<files>``. We require at
    least one commit directory that actually contains a weight file, so a
    directory left half-copied by an interrupted seed is treated as incomplete.
    """
    snapshots = os.path.join(model_dir, 'snapshots')
    if not os.path.isdir(snapshots):
        return False
    for commit in os.listdir(snapshots):
        commit_dir = os.path.join(snapshots, commit)
        if not os.path.isdir(commit_dir):
            continue
        try:
            files = os.listdir(commit_dir)
        except OSError:
            continue
        if any(weight in files for weight in _WEIGHT_FILES):
            return True
    return False


def seed_bundled_embeddings(target_dir: str | None = None) -> list[str]:
    """Copy bundled model snapshots from the image staging dir into ``target_dir``.

    Idempotent and crash-safe:
    - models already present and complete in the target are left untouched;
    - a present but incomplete model dir is removed and re-seeded;
    - each copy goes to ``<dst>.seed-tmp`` first and is then atomically renamed,
      so an interrupted run never exposes a partial snapshot;
    - a missing staging dir (slim builds, source installs) is a no-op.

    Returns the list of snapshot names that were newly seeded.
    """
    if not os.path.isdir(BUNDLED_MODELS_DIR):
        log.debug('Bundled models dir %s not present; skipping seed', BUNDLED_MODELS_DIR)
        return []

    if not target_dir:
        target_dir = os.getenv(
            'SENTENCE_TRANSFORMERS_HOME', '/app/backend/data/cache/embedding/models'
        )

    seeded = []
    for entry in sorted(os.listdir(BUNDLED_MODELS_DIR)):
        if not entry.startswith('models--'):
            # Skip cache metadata (CACHEDIR.TAG, .locks, xet, ...); only the
            # snapshot directories themselves are needed for offline loading.
            continue
        src = os.path.join(BUNDLED_MODELS_DIR, entry)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(target_dir, entry)
        if os.path.exists(dst):
            if _is_snapshot_complete(dst):
                log.debug('Bundled model %s already present and complete; skipping', entry)
                continue
            log.warning('Bundled model %s present but incomplete; re-seeding', entry)
            shutil.rmtree(dst, ignore_errors=True)

        tmp = dst + '.seed-tmp'
        try:
            os.makedirs(target_dir, exist_ok=True)
            shutil.rmtree(tmp, ignore_errors=True)
            # Preserve the HuggingFace cache layout (blobs + snapshot symlinks)
            # so loading resolves through the same paths as a native download.
            shutil.copytree(src, tmp, symlinks=True)
            # Atomic swap: only a fully-copied directory ever appears as `dst`.
            os.replace(tmp, dst)
            seeded.append(entry)
            log.info('Seeded bundled embedding model: %s', entry)
        except OSError as e:
            log.warning('Failed to seed bundled embedding model %s: %s', entry, e)
            shutil.rmtree(tmp, ignore_errors=True)
    return seeded
