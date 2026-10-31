"""Train, export and offline inference entry points. Heavy libraries load on demand."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import yaml

from .config import load_profile
from .inference import create_detector


def detect_main():
    parser = argparse.ArgumentParser(description="Detect an image/video/camera with a runtime profile")
    parser.add_argument("--config", type=Path, default=Path("configs/runtime/generic.yaml"))
    parser.add_argument("--weights-dir", type=Path, default=Path("weights"))
    parser.add_argument("--source", required=True, help="image, directory, video or camera index")
    parser.add_argument("--output", type=Path, default=Path("runs/detect"))
    parser.add_argument("--save-images", action="store_true")
    args = parser.parse_args()
    profile = load_profile(args.config)
    detector = create_detector(profile.model, args.weights_dir)
    import cv2

    source = Path(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    counter = 0

    def process(frame, name):
        nonlocal counter
        detections = detector.detect(frame)
        record = {"source": name, "frame": counter, "width": frame.shape[1],
                  "height": frame.shape[0], "detections": [
                      dict(asdict(detection), center=detection.center) for detection in detections
                  ]}
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        if args.save_images:
            for detection in detections:
                x1, y1, x2, y2 = map(int, detection.xyxy)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, detection.class_name, (x1, max(15, y1-5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            if not cv2.imwrite(str(args.output / f"frame_{counter:06d}.jpg"), frame):
                raise OSError("Failed to save annotated image")
        counter += 1

    with (args.output / "detections.jsonl").open("w", encoding="utf-8") as stream:
        if source.is_dir() or source.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
            images = sorted(p for p in source.iterdir() if p.suffix.lower() in {
                ".jpg", ".jpeg", ".png", ".bmp"
            }) if source.is_dir() else [source]
            if not images:
                raise ValueError(f"No images in {source}")
            for image in images:
                frame = cv2.imread(str(image))
                if frame is None:
                    raise ValueError(f"Cannot decode image: {image}")
                process(frame, str(image))
        else:
            capture = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
            try:
                if not capture.isOpened():
                    raise OSError(f"Cannot open source: {args.source}")
                while True:
                    ok, frame = capture.read()
                    if not ok:
                        break
                    process(frame, args.source)
            finally:
                capture.release()
    print(f"Processed {counter} frames; results: {args.output.resolve()}")


def train_main():
    parser = argparse.ArgumentParser(description="Train from a portable YAML configuration")
    parser.add_argument("--config", type=Path, default=Path("configs/training/citrus.yaml"))
    parser.add_argument("--weights-dir", type=Path, default=Path("weights"))
    parser.add_argument("--project", type=Path, default=Path("runs/train"))
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--device")
    args = parser.parse_args()
    settings = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    weights = Path(settings.pop("model")).expanduser()
    if not weights.is_absolute():
        weights = args.weights_dir / weights
    if not weights.is_file():
        raise FileNotFoundError(f"Prepare pretrained weights first: {weights}")
    data_file = (args.config.resolve().parent / settings.pop("data")).resolve()
    data = yaml.safe_load(data_file.read_text(encoding="utf-8"))
    data["path"] = str((data_file.parent / data.get("path", ".")).resolve())
    for split in ("train", "val"):
        if not (Path(data["path"]) / data[split]).is_dir():
            raise FileNotFoundError(f"Missing dataset {split}: {data['path']}/{data[split]}")
    args.project.mkdir(parents=True, exist_ok=True)
    resolved = args.project.resolve() / "dataset.resolved.yaml"
    resolved.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    for key in ("epochs", "device"):
        if getattr(args, key) is not None:
            settings[key] = getattr(args, key)
    from ultralytics import YOLO

    model = YOLO(str(weights.resolve()), task="detect")
    model.train(data=str(resolved), project=str(args.project.resolve()), **settings)
    save_dir = Path(model.trainer.save_dir)
    (save_dir / "training_config.yaml").write_text(yaml.safe_dump({
        "model": str(weights.resolve()), "data": str(data_file), **settings
    }, allow_unicode=True, sort_keys=False))
    print(f"Best checkpoint (if saved by trainer): {save_dir / 'weights/best.pt'}")


def export_main():
    parser = argparse.ArgumentParser(description="Export weights; RKNN conversion is optional and unvalidated")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--format", choices=["onnx", "rknn"], default="onnx")
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()
    if not args.weights.is_file():
        raise FileNotFoundError(args.weights)
    from ultralytics import YOLO

    options = {"format": args.format, "imgsz": args.imgsz}
    if args.format == "rknn":
        options["name"] = "rk3588"
    print(YOLO(str(args.weights.resolve()), task="detect").export(**options))
