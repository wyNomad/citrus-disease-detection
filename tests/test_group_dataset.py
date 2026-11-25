import json
from pathlib import Path

import pytest

from citrus_vision.group_dataset import (build_group_dataset, build_test_dataset,
                                         collect_pairs, load_class_names)

# 每个分组一个样本，覆盖合并逻辑需要的全部字母目录
SAMPLES = (
    ("A", "train", "S1", "a1"), ("A", "train", "S2", "a2"), ("A", "val", "S1", "a3"),
    ("B", "train", "S3", "b1"), ("B", "val", "S3", "b2"),
    ("C", "train", "S5", "c1"), ("C", "val", "S5", "c2"),
    ("D", "train", "S8", "d1"), ("D", "val", "S8", "d2"),
    ("E", "train", "S13", "e1"), ("E", "val", "S13", "e2"),
)


def write_class_table(path: Path) -> Path:
    path.write_text(json.dumps([
        {"id": 0, "name": "S0 others"},
        {"id": 1, "name": "S1 Healthy fruit"},
        {"id": 2, "name": "S2 Healthy leaf"},
        {"id": 3, "name": "S3 Blotchy mottling"},
        {"id": 5, "name": "S5 Zinc deficiency"},
        {"id": 8, "name": "S8 Magnesium deficiency"},
        {"id": 13, "name": "S13 Sooty mould"},
    ]), encoding="utf-8")
    return path


def make_source(root: Path) -> Path:
    """Build a miniature source tree in the grouped layout of the public dataset."""
    for group, split, symptom, stem in SAMPLES:
        images = root / f"{group}-{split}" / symptom / "images"
        labels = root / f"{group}-{split}" / symptom / "labels"
        images.mkdir(parents=True, exist_ok=True)
        labels.mkdir(parents=True, exist_ok=True)
        (images / f"{stem}.jpg").write_bytes(b"image")
        (labels / f"{stem}.txt").write_text("0 0.5 0.5 0.2 0.2\n")
    (root / "testA" / "images").mkdir(parents=True)
    (root / "testA" / "labels").mkdir(parents=True)
    for name in ("t1", "t2"):
        (root / "testA" / "images" / f"{name}.jpg").write_bytes(b"image")
        (root / "testA" / "labels" / f"{name}.txt").write_text("1 0.4 0.4 0.2 0.2\n")
    write_class_table(root / "A-train" / "label_object.json")
    return root


def class_file(source: Path) -> Path:
    return source / "A-train" / "label_object.json"


def test_group_merge_respects_requested_groups(tmp_path):
    source = make_source(tmp_path / "source")
    narrow, wide = tmp_path / "abc", tmp_path / "abcde"
    build_group_dataset(source, narrow, "ABC", class_file(source))
    build_group_dataset(source, wide, "ABCDE", class_file(source))

    assert sorted(p.name for p in (narrow / "images/train").iterdir()) == \
        ["a1.jpg", "a2.jpg", "b1.jpg", "c1.jpg"]
    assert sorted(p.name for p in (narrow / "images/val").iterdir()) == \
        ["a3.jpg", "b2.jpg", "c2.jpg"]
    # 宽组在窄组基础上追加 D、E，且不覆盖已有划分
    extra = {p.name for p in (wide / "images/train").iterdir()} - \
        {p.name for p in (narrow / "images/train").iterdir()}
    assert extra == {"d1.jpg", "e1.jpg"}
    assert len(list((wide / "labels/val").glob("*.txt"))) == 5


def test_class_ids_are_not_renumbered(tmp_path):
    source = make_source(tmp_path / "source")
    assert load_class_names(class_file(source))[0] == "S0 others"

    root = tmp_path / "abc"
    build_group_dataset(source, root, "ABC", class_file(source))
    text = (root / "data.yaml").read_text(encoding="utf-8")
    assert "  0: S0 others" in text
    assert "  13: S13 Sooty mould" in text
    assert f"path: {root.resolve()}" in text


def test_existing_output_is_never_deleted(tmp_path):
    source = make_source(tmp_path / "source")
    output = tmp_path / "abc"
    output.mkdir()
    marker = output / "important.txt"
    marker.write_text("keep")

    with pytest.raises(FileExistsError):
        build_group_dataset(source, output, "ABC", class_file(source))
    assert marker.read_text() == "keep"


def test_image_without_label_is_reported(tmp_path):
    source = make_source(tmp_path / "source")
    (source / "A-train" / "S1" / "labels" / "a1.txt").unlink()

    with pytest.raises(RuntimeError, match="without labels"):
        collect_pairs(source, "ABC", "train")


def test_unknown_group_is_rejected(tmp_path):
    source = make_source(tmp_path / "source")
    with pytest.raises(ValueError, match="Unknown group"):
        build_group_dataset(source, tmp_path / "x", "AB", class_file(source))


def test_test_partition_stays_out_of_training_splits(tmp_path):
    source = make_source(tmp_path / "source")
    root = tmp_path / "lab_testA"
    build_test_dataset(source, root, "testA", class_file(source))

    assert sorted(p.name for p in (root / "images").iterdir()) == ["t1.jpg", "t2.jpg"]
    assert "test: images" in (root / "data.yaml").read_text(encoding="utf-8")
    assert not (root / "images/train").exists()
