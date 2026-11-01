import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from citrus_vision import cli


def dataset(tmp_path):
    data = tmp_path / "data"
    (data / "images/val").mkdir(parents=True)
    config = tmp_path / "dataset.yaml"
    config.write_text("path: data\ntrain: images/train\nval: images/val\nnames:\n  0: leaf\n")
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"test weights")
    return config, weights


def test_evaluation_saves_metrics_config_and_correct_split_without_training_data(tmp_path, monkeypatch):
    data, weights = dataset(tmp_path)
    output = tmp_path / "result"
    calls = []

    class FakeModel:
        names = {0: "leaf"}

        def __init__(self, *args, **kwargs):
            pass

        def val(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(results_dict={"metrics/mAP50(B)": np.float32(.5)})

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeModel))
    monkeypatch.setattr(sys, "argv", ["val", "--weights", str(weights), "--data", str(data),
                                    "--output", str(output), "--imgsz", "64"])
    cli.val_main()
    assert calls[0]["split"] == "val" and calls[0]["imgsz"] == 64
    assert Path(calls[0]["data"]) == output / "dataset.yaml"
    assert json.loads((output / "metrics.json").read_text())["metrics/mAP50(B)"] == .5
    metadata = yaml.safe_load((output / "validation_config.yaml").read_text())
    assert metadata["weights_sha256"] == hashlib.sha256(weights.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        cli.val_main()
    assert json.loads((output / "metrics.json").read_text())["metrics/mAP50(B)"] == .5


def test_evaluation_rejects_wrong_model_labels_before_creating_output(tmp_path, monkeypatch):
    data, weights = dataset(tmp_path)
    output = tmp_path / "result"
    fake = SimpleNamespace(names={0: "person"})
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=lambda *args, **kwargs: fake))
    monkeypatch.setattr(sys, "argv", ["val", "--weights", str(weights), "--data", str(data),
                                    "--output", str(output)])
    with pytest.raises(ValueError, match="class mappings differ"):
        cli.val_main()
    assert not output.exists()


def test_detector_command_overrides_profile_without_modifying_it(tmp_path, monkeypatch):
    cv2 = pytest.importorskip("cv2")
    profile = tmp_path / "profile.yaml"
    profile.write_text("model:\n  path: configured.pt\n  confidence: 0.9\n  target_classes: [leaf]\n")
    image = tmp_path / "image.jpg"
    assert cv2.imwrite(str(image), np.zeros((8, 8, 3), np.uint8))
    configs = []

    def create(config, weights_dir):
        configs.append(config)
        return SimpleNamespace(detect=lambda frame: [])

    monkeypatch.setattr(cli, "create_detector", create)
    monkeypatch.setattr(sys, "argv", ["detect", "--config", str(profile), "--source", str(image),
                                    "--output", str(tmp_path / "result"), "--model", "chosen.pt",
                                    "--conf", "0", "--iou", "0.6", "--imgsz", "64",
                                    "--device", "cpu", "--classes"])
    cli.detect_main()
    assert configs[0].path == "chosen.pt" and configs[0].confidence == 0
    assert configs[0].image_size == 64 and configs[0].iou == .6
    assert configs[0].target_classes == []
    assert yaml.safe_load(profile.read_text())["model"]["confidence"] == .9


def test_export_records_model_contract_and_forwarded_options(tmp_path, monkeypatch):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"original model")
    exported = tmp_path / "best.onnx"
    calls = []

    class FakeModel:
        names = {0: "leaf"}

        def __init__(self, *args, **kwargs):
            pass

        def export(self, **kwargs):
            calls.append(kwargs)
            exported.write_bytes(b"exported model")
            return str(exported)

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeModel))
    monkeypatch.setattr(sys, "argv", ["export", "--weights", str(weights), "--imgsz", "64",
                                    "--opset", "17", "--dynamic"])
    cli.export_main()
    assert calls[0]["opset"] == 17 and calls[0]["dynamic"]
    metadata = json.loads(exported.with_suffix(".onnx.json").read_text())
    assert metadata["source_sha256"] == hashlib.sha256(weights.read_bytes()).hexdigest()
    assert metadata["artifact_sha256"] == hashlib.sha256(exported.read_bytes()).hexdigest()
    assert metadata["class_names"] == {"0": "leaf"}
    assert metadata["requested_image_size"] == 64


@pytest.mark.parametrize("command,arguments", [
    (cli.train_main, ["--epochs", "0"]),
    (cli.train_main, ["--workers", "-1"]),
    (cli.val_main, ["--weights", "absent.pt", "--batch", "0"]),
    (cli.export_main, ["--weights", "absent.pt", "--format", "rknn", "--dynamic"]),
    (cli.export_main, ["--weights", "absent.pt", "--format", "rknn", "--opset", "17"]),
])
def test_invalid_command_options_fail_during_argument_validation(monkeypatch, command, arguments):
    monkeypatch.setattr(sys, "argv", ["command", *arguments])
    with pytest.raises(SystemExit) as error:
        command()
    assert error.value.code == 2
