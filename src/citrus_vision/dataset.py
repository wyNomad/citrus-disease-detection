"""Assemble Ultralytics datasets without ever deleting existing ones.

Two source layouts are supported: a flat ``images``/``labels`` pair set that
must be sampled and split, and a symptom-grouped tree that must be merged.
Both refuse an existing output directory instead of overwriting it.
"""

import argparse
import json
import os
from pathlib import Path
import random
import shutil

#: Symptom groups from the source dataset, in the order the paper reports them.
SYMPTOM_GROUPS: dict[str, tuple[str, ...]] = {
    "ABC": ("A", "B", "C"),
    "ABCD": ("A", "B", "C", "D"),
    "ABCDE": ("A", "B", "C", "D", "E"),
}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
SPLITS = ("train", "val")
#: Held-out test partitions, one per acquisition environment.
TEST_PARTITIONS = ("testA", "testB", "testC")
DEFAULT_CLASS_FILE = Path("A-train/label_object.json")


def prepare_dataset(source: Path, output: Path, sample: int = 100,
                    train_ratio: float = 0.8, seed: int = 42) -> dict:
    source, output = source.resolve(), output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("source and output must not overlap")
    if not 0 < train_ratio < 1 or sample < 0:
        raise ValueError("train_ratio must be in (0,1), sample >= 0 (0 = all)")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}; choose a new directory")
    images = source / "images"
    if not images.is_dir() or not (source / "labels").is_dir():
        raise FileNotFoundError("source must contain images/ and labels/")
    pairs = sorted(p for p in images.iterdir() if p.suffix.lower() in {
        ".jpg", ".jpeg", ".png", ".bmp"
    } and (source / "labels" / (p.stem + ".txt")).is_file())
    if len({p.stem for p in pairs}) != len(pairs):
        raise ValueError("duplicate image stems would overwrite labels")
    rng = random.Random(seed)
    rng.shuffle(pairs)
    if sample:
        pairs = pairs[:sample]
    if len(pairs) < 2:
        raise ValueError("at least two image/label pairs are required")
    split = max(1, min(len(pairs)-1, int(len(pairs) * train_ratio)))
    manifest = {"seed": seed, "source": str(source), "train": [], "val": []}
    # Claim the root exclusively before copying; a concurrent run must fail here.
    output.mkdir(parents=True, exist_ok=False)
    for name, selected in (("train", pairs[:split]), ("val", pairs[split:])):
        for kind in ("images", "labels"):
            (output / kind / name).mkdir(parents=True, exist_ok=True)
        for image in selected:
            label = source / "labels" / (image.stem + ".txt")
            shutil.copy2(image, output / "images" / name / image.name)
            shutil.copy2(label, output / "labels" / name / label.name)
            manifest[name].append(image.name)
    (output / "split_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=100, help="0 means all pairs")
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    manifest = prepare_dataset(args.source, args.output, args.sample, args.train_ratio, args.seed)
    print(json.dumps({key: len(manifest[key]) for key in ("train", "val")}))

import argparse
import json
import os
from pathlib import Path
import shutil


def load_class_names(path: Path) -> dict[int, str]:
    """Read the source dataset's label-object table and keep the original IDs."""
    table = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(table, list) or not table:
        raise ValueError(f"Class table must be a non-empty list: {path}")
    names: dict[int, str] = {}
    for item in table:
        if not isinstance(item, dict) or "id" not in item or "name" not in item:
            raise ValueError(f"Class table entries need id and name: {path}")
        names[int(item["id"])] = str(item["name"])
    return names


def collect_pairs(source: Path, group: str, split: str) -> list[tuple[Path, Path]]:
    """Return every image/label pair of one group and split, verifying 1:1 pairing."""
    pairs: list[tuple[Path, Path]] = []
    missing: list[str] = []
    for letter in SYMPTOM_GROUPS[group]:
        root = source / f"{letter}-{split}"
        if not root.is_dir():
            raise FileNotFoundError(f"Missing source directory: {root}")
        for class_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            images = class_dir / "images"
            labels = class_dir / "labels"
            if not images.is_dir():
                continue
            for image in sorted(images.iterdir()):
                if image.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                label = labels / f"{image.stem}.txt"
                if not label.is_file():
                    missing.append(str(image))
                    continue
                pairs.append((image, label))
    if missing:
        raise RuntimeError(
            f"{group}/{split} has {len(missing)} images without labels, "
            f"for example {missing[:3]}")
    if not pairs:
        raise RuntimeError(f"{group}/{split} contains no image/label pair")
    stems = {image.stem for image, _ in pairs}
    if len(stems) != len(pairs):
        raise ValueError(f"{group}/{split} has duplicate image stems that would overwrite labels")
    return pairs


def _place(source_file: Path, target: Path, mode: str) -> None:
    if mode == "copy":
        shutil.copy2(source_file, target)
    elif mode == "link":
        os.symlink(source_file.resolve(), target)
    else:
        raise ValueError(f"Unknown placement mode: {mode}")


def build_test_dataset(source: Path, output: Path, partition: str, class_file: Path,
                        mode: str = "link") -> dict:
    """Assemble one held-out test partition, keeping it out of training splits."""
    source, output = source.resolve(), output.resolve()
    root = source / partition
    images, labels = root / "images", root / "labels"
    if not images.is_dir() or not labels.is_dir():
        raise FileNotFoundError(f"Missing images/ or labels/ under {root}")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}; choose a new directory")
    names = load_class_names(class_file)

    output.mkdir(parents=True)
    (output / "images").mkdir()
    (output / "labels").mkdir()
    count = 0
    missing: list[str] = []
    for image in sorted(images.iterdir()):
        if image.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        label = labels / f"{image.stem}.txt"
        if not label.is_file():
            missing.append(image.name)
            continue
        _place(image, output / "images" / image.name, mode)
        _place(label, output / "labels" / label.name, mode)
        count += 1
    if missing:
        raise RuntimeError(f"{partition} has {len(missing)} images without labels: {missing[:3]}")

    lines = [
        f"# Test partition {partition}: generated by citrus-build-groups from {source}",
        "path: .",
        "train: images",
        "val: images",
        "test: images",
        "",
        "names:",
    ]
    lines += [f"  {class_id}: {name}" for class_id, name in sorted(names.items())]
    (output / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"test": count, "classes": len(names)}


def build_group_dataset(source: Path, output: Path, group: str, class_file: Path,
                        mode: str = "link") -> dict:
    """Assemble one grouped dataset and write its Ultralytics data YAML."""
    source, output = source.resolve(), output.resolve()
    if group not in SYMPTOM_GROUPS:
        raise ValueError(f"Unknown group {group}; expected one of {sorted(SYMPTOM_GROUPS)}")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}; choose a new directory")
    names = load_class_names(class_file)

    output.mkdir(parents=True)
    stats: dict[str, int] = {}
    for split in SPLITS:
        pairs = collect_pairs(source, group, split)
        image_dir = output / "images" / split
        label_dir = output / "labels" / split
        image_dir.mkdir(parents=True)
        label_dir.mkdir(parents=True)
        for image, label in pairs:
            _place(image, image_dir / image.name, mode)
            _place(label, label_dir / label.name, mode)
        stats[split] = len(pairs)

    lines = [
        f"# Group {group}: generated by citrus-build-groups from {source}",
        "path: .",
        "train: images/train",
        "val: images/val",
        "",
        "names:",
    ]
    lines += [f"  {class_id}: {name}" for class_id, name in sorted(names.items())]
    (output / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    stats["classes"] = len(names)
    return stats


def build_groups_main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True,
                        help="directory holding <letter>-<split>/<Sx>/ folders")
    parser.add_argument("--output", type=Path, required=True,
                        help="new directory for the assembled dataset")
    parser.add_argument("--group", action="append", choices=sorted(SYMPTOM_GROUPS),
                        help="group to build; repeat for several, default builds all")
    parser.add_argument("--class-file", type=Path,
                        help=f"label-object JSON, default <source>/{DEFAULT_CLASS_FILE}")
    parser.add_argument("--test", action="append", choices=list(TEST_PARTITIONS),
                        help="held-out partition to assemble; repeat for several")
    parser.add_argument("--copy", action="store_true",
                        help="copy files instead of symlinking them")
    args = parser.parse_args()

    class_file = args.class_file or (args.source / DEFAULT_CLASS_FILE)
    mode = "copy" if args.copy else "link"
    for group in args.group or list(SYMPTOM_GROUPS):
        target = args.output / f"lab_{group.lower()}"
        stats = build_group_dataset(args.source, target, group, class_file, mode)
        print(f"{group}: train={stats['train']} val={stats['val']} classes={stats['classes']}"
              f" -> {target}")
    for partition in args.test or ():
        target = args.output / f"lab_{partition}"
        stats = build_test_dataset(args.source, target, partition, class_file, mode)
        print(f"{partition}: test={stats['test']} classes={stats['classes']} -> {target}")


if __name__ == "__main__":
    main()
