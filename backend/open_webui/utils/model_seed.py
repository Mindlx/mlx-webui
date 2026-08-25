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
"""

import logging
import os
import shutil

log = logging.getLogger(__name__)

# Path baked at image build time, deliberately outside /app/backend/data so a
# bind mount over the data volume can never hide it. Overridable via env for
# non-Docker/local installs.
BUNDLED_MODELS_DIR = os.getenv('BUNDLED_MODELS_DIR', '/opt/open-webui/embedding_models')


def seed_bundled_embeddings(target_dir: str | None = None) -> list[str]:
    """Copy bundled model snapshots from the image staging dir into ``target_dir``.

    Idempotent: entries already present in the target are left untouched, and
    a missing staging dir (e.g. slim builds, source installs) is a no-op.

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
            log.debug('Bundled model %s already present; skipping', entry)
            continue
        try:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copytree(src, dst)
            seeded.append(entry)
            log.info('Seeded bundled embedding model: %s', entry)
        except OSError as e:
            log.warning('Failed to seed bundled embedding model %s: %s', entry, e)
    return seeded
