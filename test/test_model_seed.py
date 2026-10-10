"""Tests for open_webui.utils.model_seed."""

import os
from unittest.mock import patch

from open_webui.utils.model_seed import seed_bundled_embeddings


def _make_snapshot(root, name, weight='model.safetensors'):
    """Create a complete HF-style snapshot (requires a weight file)."""
    model_dir = os.path.join(root, name, 'snapshots', 'abc123')
    os.makedirs(model_dir)
    with open(os.path.join(model_dir, 'config.json'), 'w') as f:
        f.write('{}')
    if weight:
        with open(os.path.join(model_dir, weight), 'w') as f:
            f.write('weights')
    return os.path.join(root, name)


def test_seeds_missing_models(tmp_path):
    bundled = tmp_path / 'bundled'
    target = tmp_path / 'target'
    bundled.mkdir()
    _make_snapshot(str(bundled), 'models--test--model-a')
    _make_snapshot(str(bundled), 'models--test--model-b')

    with patch('open_webui.utils.model_seed.BUNDLED_MODELS_DIR', str(bundled)):
        seeded = seed_bundled_embeddings(str(target))

    assert sorted(seeded) == ['models--test--model-a', 'models--test--model-b']
    assert os.path.exists(
        str(target / 'models--test--model-a' / 'snapshots' / 'abc123' / 'model.safetensors')
    )


def test_skips_existing_complete_models(tmp_path):
    bundled = tmp_path / 'bundled'
    target = tmp_path / 'target'
    bundled.mkdir()
    target.mkdir()
    _make_snapshot(str(bundled), 'models--test--model-a')
    _make_snapshot(str(bundled), 'models--test--model-b')
    # pre-seed model-a completely in target
    _make_snapshot(str(target), 'models--test--model-a')

    with patch('open_webui.utils.model_seed.BUNDLED_MODELS_DIR', str(bundled)):
        seeded = seed_bundled_embeddings(str(target))

    assert seeded == ['models--test--model-b']


def test_reseeds_incomplete_model(tmp_path):
    """A present-but-incomplete snapshot (no weight file) must be re-seeded."""
    bundled = tmp_path / 'bundled'
    target = tmp_path / 'target'
    bundled.mkdir()
    target.mkdir()
    _make_snapshot(str(bundled), 'models--test--model-a')
    # incomplete leftover in target: snapshots dir exists but has no weight file
    _make_snapshot(str(target), 'models--test--model-a', weight=None)

    with patch('open_webui.utils.model_seed.BUNDLED_MODELS_DIR', str(bundled)):
        seeded = seed_bundled_embeddings(str(target))

    assert seeded == ['models--test--model-a']
    assert os.path.exists(
        str(target / 'models--test--model-a' / 'snapshots' / 'abc123' / 'model.safetensors')
    )


def test_no_partial_leftover_after_seed(tmp_path):
    """Seeding must not leave a .seed-tmp directory behind."""
    bundled = tmp_path / 'bundled'
    target = tmp_path / 'target'
    bundled.mkdir()
    _make_snapshot(str(bundled), 'models--test--model-a')

    with patch('open_webui.utils.model_seed.BUNDLED_MODELS_DIR', str(bundled)):
        seed_bundled_embeddings(str(target))

    leftovers = [e for e in os.listdir(str(target)) if e.endswith('.seed-tmp')]
    assert leftovers == []


def test_missing_bundled_dir_is_noop(tmp_path):
    with patch('open_webui.utils.model_seed.BUNDLED_MODELS_DIR', str(tmp_path / 'nope')):
        assert seed_bundled_embeddings(str(tmp_path / 'target')) == []
