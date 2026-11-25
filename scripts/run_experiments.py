"""Run the configured training and evaluation matrix for the disease dataset.

Each entry trains once and is then evaluated on its own validation split plus
every held-out acquisition environment. Training and evaluation reuse the
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


def collect(name: str, dataset: str, tests: list[str], val_root: Path) -> dict:
    record = {"run": name, "metrics": {}}
    targets = [("val", f"{name}-val")] + [(t, f"{name}-{t}") for t in tests]
    for tag, folder in targets:
        path = val_root / folder / "metrics.json"
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
    tests = list(matrix.get("tests", []))
    project = (ROOT / args.project).resolve()
    val_root = project / "val"
    project.mkdir(parents=True, exist_ok=True)
    prepare_environment(project)

    for entry in matrix["runs"]:
        config = ROOT / entry["config"]
        settings = yaml.safe_load(config.read_text(encoding="utf-8"))
        name = settings.get("name") or config.stem
        if args.only and name not in args.only:
            continue
        print(f"\n=== {name} ===", flush=True)

        weights = (project / "train" / name / "weights" / "best.pt")
        if not args.eval_only:
            if weights.is_file():
                print(f"  existing checkpoint, skipping training: {weights}", flush=True)
            else:
                arguments = ["--config", str(config), "--weights-dir", str(ROOT / args.weights_dir),
                             "--project", str(project / "train"), "--device", args.device]
                for flag, value in (("--epochs", args.epochs), ("--batch", args.batch),
                                    ("--workers", args.workers)):
                    if value is not None:
                        arguments += [flag, str(value)]
                if run(TRAIN_CALL, arguments) != 0:
                    print(f"  training failed, skipping evaluation", flush=True)
                    continue
        if not weights.is_file():
            print(f"  missing checkpoint: {weights}", flush=True)
            continue

        targets = [(entry["dataset"], "val")] + [(t, "test") for t in tests]
        for dataset, split in targets:
            tag = f"{name}-{'val' if split == 'val' else dataset}"
            output = val_root / tag
            if output.exists():
                print(f"  existing evaluation, skipping: {output.name}", flush=True)
                continue
            run(VAL_CALL, ["--weights", str(weights),
                           "--data", str(ROOT / "configs/datasets" / f"{dataset}.yaml"),
                           "--output", str(output), "--split", split,
                           "--imgsz", str(settings.get("imgsz", 640)),
                           "--batch", str(min(args.batch or 8, 8)),
                           "--device", args.device])

    summary = project / "summary.json"
    records = [collect((yaml.safe_load((ROOT / e["config"]).read_text(encoding="utf-8")).get("name")
                        or Path(e["config"]).stem),
                       e["dataset"], tests, val_root) for e in matrix["runs"]]
    summary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nMetrics summary: {summary}")


if __name__ == "__main__":
    main()
