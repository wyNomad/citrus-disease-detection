import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

from citrus_vision.cli import train_main


def test_training_resolves_dataset_relative_to_config_not_working_directory(tmp_path, monkeypatch):
    config_dir = tmp_path / "project/configs/training"
    config_dir.mkdir(parents=True)
    data_config = config_dir.parent / "datasets/citrus.yaml"
    data_config.parent.mkdir()
    dataset = tmp_path / "project/data/small"
    for split in ("train", "val"):
        (dataset / "images" / split).mkdir(parents=True)
    data_config.write_text("path: ../../data/small\ntrain: images/train\nval: images/val\nnames:\n  0: leaf\n")
    config = config_dir / "train.yaml"
    config.write_text("model: initial.pt\ndata: ../datasets/citrus.yaml\nepochs: 10\nname: citrus\n")
    weights = tmp_path / "weights"
    weights.mkdir()
    (weights / "initial.pt").touch()
    outputs = tmp_path / "outputs"
    actual = outputs / "citrus2"
    calls = []

    class FakeYolo:
        def __init__(self, path, task):
            assert path == str(weights / "initial.pt")
            self.trainer = SimpleNamespace(save_dir=actual)

        def train(self, **kwargs):
            calls.append(kwargs)
            actual.mkdir()

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYolo))
    monkeypatch.setattr(sys, "argv", ["citrus-train", "--config", str(config), "--weights-dir", str(weights),
                                    "--project", str(outputs), "--epochs", "1"])
    monkeypatch.chdir(tmp_path)
    train_main()
    resolved = yaml.safe_load(Path(calls[0]["data"]).read_text())
    assert resolved["path"] == str(dataset)
    assert calls[0]["epochs"] == 1
    assert (actual / "training_config.yaml").is_file()


def test_two_training_runs_keep_independent_dataset_snapshots(tmp_path, monkeypatch):
    weights = tmp_path / "model.pt"
    weights.touch()
    project = tmp_path / "runs"
    references = []

    class FakeYolo:
        def __init__(self, *args, **kwargs):
            pass

        def train(self, **kwargs):
            references.append(Path(kwargs["data"]))
            actual = project / f"experiment{len(references)}"
            actual.mkdir()
            self.trainer = SimpleNamespace(save_dir=actual)

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYolo))
    for index in (1, 2):
        data = tmp_path / f"data{index}"
        for split in ("train", "val"):
            (data / "images" / split).mkdir(parents=True)
        data_yaml = tmp_path / f"data{index}.yaml"
        data_yaml.write_text(yaml.safe_dump(dict(path=str(data), train="images/train",
                                               val="images/val", names={0: "leaf"})))
        config = tmp_path / f"train{index}.yaml"
        config.write_text(yaml.safe_dump(dict(model=str(weights), data=str(data_yaml))))
        monkeypatch.setattr(sys, "argv", ["train", "--config", str(config), "--project", str(project)])
        train_main()
    assert references[0] != references[1]
    for index, path in enumerate(references, 1):
        assert yaml.safe_load(path.read_text())["path"] == str(tmp_path / f"data{index}")
        metadata = yaml.safe_load((project / f"experiment{index}/training_config.yaml").read_text())
        assert metadata["resolved_data"] == str(path)
