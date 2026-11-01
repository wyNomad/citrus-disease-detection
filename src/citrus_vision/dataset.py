"""Reproducible image/label pair splitting without deleting existing datasets."""

import argparse
import json
from pathlib import Path
import random
import shutil


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
