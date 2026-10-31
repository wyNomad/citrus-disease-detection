import sys
from types import SimpleNamespace

import numpy as np
import pytest

from citrus_vision.config import ModelConfig
from citrus_vision.inference import create_detector


def test_shared_adapter_preserves_original_pixels_and_class_filter(tmp_path, monkeypatch):
    calls = []
    class FakeYolo:
        names = {0: "bottle", 1: "person"}

        def __init__(self, path, task):
            assert task == "detect"

        def predict(self, **kwargs):
            calls.append(kwargs)
            return [SimpleNamespace(boxes=[SimpleNamespace(
                cls=np.array([0]), conf=np.array([.9]), xyxy=np.array([[10, 20, 30, 60]])
            )])]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYolo))
    (tmp_path / "test.pt").touch()
    detector = create_detector(ModelConfig(path="test.pt", target_classes=["bottle"]), tmp_path)
    result = detector.detect(np.zeros((100, 200, 3), np.uint8))
    assert result[0].center == (20, 40)
    assert result[0].xyxy == (10, 20, 30, 60)
    assert result[0].class_name == "bottle"
    assert calls[0]["classes"] == [0]
    with pytest.raises(ValueError, match="not present"):
        create_detector(ModelConfig(path="test.pt", target_classes=["missing"]), tmp_path)
