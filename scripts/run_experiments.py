"""Run the configured training and evaluation matrix for the disease dataset.

Every entry trains once and is then evaluated on its own validation split plus
each held-out acquisition environment. Training and evaluation reuse the
``citrus-train`` and ``citrus-val`` entry points so configuration snapshots,
class-mapping checks and weight hashes keep their existing behaviour.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
TRAIN_CALL = "from citrus_vision.cli import train_main; train_main()"
VAL_CALL = "from citrus_vision.cli import val_main; val_main()"


def prepare_environment(project: Path) -> None:
    """Keep Ultralytics state inside the project and reuse a bundled font."""
    config_dir = project / "yolo-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(config_dir)
    for key, value in (("YOLO_OFFLINE", "true"), ("YOLO_AUTOINSTALL", "false"),
                       ("WANDB_MODE", "disabled")):
        os.environ.setdefault(key, value)
    import matplotlib
    from ultralytics.utils import USER_CONFIG_DIR

    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    font = Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"
    target = USER_CONFIG_DIR / "Arial.ttf"
    if font.is_file() and not target.exists():
        shutil.copy2(font, target)


def run(call: str, arguments: list[str]) -> int:
    command = [sys.executable, "-c", call, *arguments]
    print("$ " + " ".join(command[2:]), flush=True)
    return subprocess.run(command, cwd=ROOT).returncode


def tag_of(dataset: Path) -> str:
    """Name the evaluation run after the dataset folder, e.g. ``lab_testA``."""
    return dataset.parent.name


def collect(name: str, tags: list[str], val_root: Path) -> dict:
    record = {"run": name, "metrics": {}}
    for tag in tags:
        path = val_root / f"{name}-{tag}" / "metrics.json"
        record["metrics"][tag] = (json.loads(path.read_text(encoding="utf-8"))
                                  if path.is_file() else None)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", type=Path, default=Path("configs/experiments/lab.yaml"))
    parser.add_argument("--project", type=Path, default=Path("runs"))
    parser.add_argument("--weights-dir", type=Path, default=Path("weights"))
    parser.add_argument("--device", default="cpu", help="0 for the first GPU, cpu for local runs")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--only", nargs="*", help="restrict to these run names")
    parser.add_argument("--eval-only", action="store_true", help="skip training, evaluate only")
    args = parser.parse_args()

    matrix = yaml.safe_load(args.matrix.read_text(encoding="utf-8"))
    config = (ROOT / matrix["config"]).resolve()
    settings = yaml.safe_load(config.read_text(encoding="utf-8"))
    tests = [(ROOT / item).resolve() for item in matrix.get("tests", [])]
    project = (ROOT / args.project).resolve()
    val_root = project / "val"
    project.mkdir(parents=True, exist_ok=True)
    prepare_environment(project)

    for entry in matrix["runs"]:
        name = entry["name"]
        dataset = (ROOT / entry["data"]).resolve()
        if args.only and name not in args.only:
            continue
        print(f"\n=== {name} ===", flush=True)

        weights = project / "train" / name / "weights" / "best.pt"
        if not args.eval_only:
            if weights.is_file():
                print(f"  existing checkpoint, skipping training: {weights}", flush=True)
            else:
                arguments = ["--config", str(config), "--data", str(dataset),
                             "--weights-dir", str(ROOT / args.weights_dir),
                             "--project", str(project / "train"), "--name", name,
                             "--device", args.device]
                for flag, value in (("--epochs", args.epochs), ("--batch", args.batch),
                                    ("--workers", args.workers)):
                    if value is not None:
                        arguments += [flag, str(value)]
                if run(TRAIN_CALL, arguments) != 0:
                    print("  training failed, skipping evaluation", flush=True)
                    continue
        if not weights.is_file():
            print(f"  missing checkpoint: {weights}", flush=True)
            continue

        targets = [("val", dataset)] + [(tag_of(t), t) for t in tests]
        for tag, data_path in targets:
            output = val_root / f"{name}-{tag}"
            if output.exists():
                print(f"  existing evaluation, skipping: {output.name}", flush=True)
                continue
            split = "val" if tag == "val" else "test"
            run(VAL_CALL, ["--weights", str(weights), "--data", str(data_path),
                           "--output", str(output), "--split", split,
                           "--imgsz", str(settings.get("imgsz", 640)),
                           "--batch", str(min(args.batch or 8, 8)),
                           "--device", args.device])

    records = [collect(e["name"], ["val"] + [tag_of(t) for t in tests], val_root)
               for e in matrix["runs"]]
    summary = project / "summary.json"
    summary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nMetrics summary: {summary}")


if __name__ == "__main__":
    main()
