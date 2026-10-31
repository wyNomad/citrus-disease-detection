from pathlib import Path

import pytest

from citrus_vision.dataset import prepare_dataset


def make_source(path: Path):
    (path / "images").mkdir(parents=True)
    (path / "labels").mkdir()
    for index in range(10):
        (path / "images" / f"{index}.jpg").write_bytes(b"sample")
        (path / "labels" / f"{index}.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    (path / "images" / "unlabelled.jpg").touch()


def test_split_is_reproducible_and_only_includes_pairs(tmp_path):
    source = tmp_path / "source"
    make_source(source)
    first = prepare_dataset(source, tmp_path / "first", sample=6)
    second = prepare_dataset(source, tmp_path / "second", sample=6)
    assert first == second
    assert len(first["train"]) == 4 and len(first["val"]) == 2
    assert not set(first["train"]) & set(first["val"])
    assert "unlabelled.jpg" not in first["train"] + first["val"]


def test_existing_output_is_never_deleted(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    make_source(source)
    output.mkdir()
    marker = output / "important.txt"
    marker.write_text("keep")
    with pytest.raises(FileExistsError):
        prepare_dataset(source, output)
    assert marker.read_text() == "keep"


def test_overlapping_paths_are_rejected(tmp_path):
    make_source(tmp_path / "source")
    with pytest.raises(ValueError, match="overlap"):
        prepare_dataset(tmp_path / "source", tmp_path / "source/output")
