"""Tests for open_webui.utils.model_seed."""

import os
from unittest.mock import patch

from open_webui.utils.model_seed import seed_bundled_embeddings


def _make_snapshot(root, name):
    model_dir = os.path.join(root, name, 'snapshots', 'abc123')
    os.makedirs(model_dir)
    with open(os.path.join(model_dir, 'model.safetensors'), 'w') as f:
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


def test_skips_existing_models(tmp_path):
    bundled = tmp_path / 'bundled'
    target = tmp_path / 'target'
    bundled.mkdir()
    target.mkdir()
    _make_snapshot(str(bundled), 'models--test--model-a')
    _make_snapshot(str(bundled), 'models--test--model-b')
    # pre-seed model-a in target
    _make_snapshot(str(target), 'models--test--model-a')

    with patch('open_webui.utils.model_seed.BUNDLED_MODELS_DIR', str(bundled)):
        seeded = seed_bundled_embeddings(str(target))

    assert seeded == ['models--test--model-b']


def test_missing_bundled_dir_is_noop(tmp_path):
    with patch('open_webui.utils.model_seed.BUNDLED_MODELS_DIR', str(tmp_path / 'nope')):
        assert seed_bundled_embeddings(str(tmp_path / 'target')) == []
