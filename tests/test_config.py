from pathlib import Path

import pytest

from citrus_vision.config import load_profile, resolve_model_path, ModelConfig, LocalizationConfig
from citrus_vision.inference import create_detector


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["generic", "citrus"])
def test_profiles_load_without_model_or_ros(name):
    assert load_profile(ROOT / f"configs/runtime/{name}.yaml").model.backend == "ultralytics"


def test_model_paths_can_move_with_weights_directory(tmp_path):
    weights = tmp_path / "moved" / "weights"
    weights.mkdir(parents=True)
    model = weights / "model.pt"
    model.touch()
    assert resolve_model_path(ModelConfig(path="model.pt"), weights) == model


def test_missing_weights_fail_before_loading_framework(tmp_path):
    with pytest.raises(FileNotFoundError, match="no automatic download"):
        resolve_model_path(ModelConfig(path="missing.pt"), tmp_path)


def test_rknn_is_explicitly_unimplemented(tmp_path):
    with pytest.raises(NotImplementedError, match="not board-validated"):
        create_detector(ModelConfig(path="x.rknn", backend="rknn"), tmp_path)


@pytest.mark.parametrize("kwargs", [
    {"depth_scale": 0}, {"min_depth": 2, "max_depth": 1},
    {"sample_radius": -1}, {"sync_queue": 0}, {"sync_slop": float("nan")},
])
def test_invalid_localization_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        LocalizationConfig(**kwargs)


def test_profile_typo_is_not_silently_ignored(tmp_path):
    file = tmp_path / "config.yaml"
    file.write_text("model:\n  path: x.pt\npublish_annotated: 'false'\n")
    with pytest.raises(ValueError, match="boolean"):
        load_profile(file)
