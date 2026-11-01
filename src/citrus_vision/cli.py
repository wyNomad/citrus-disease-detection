"""Train, evaluate, export and offline inference entry points. Load heavy libraries on demand."""

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import tempfile

import yaml

from .config import load_profile
from .inference import create_detector


def _dataset_config(path: Path, splits: tuple[str, ...]) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("names"), (dict, list)) or not data["names"]:
        raise ValueError("Dataset YAML must contain a names mapping or list")
    data["path"] = str((path.parent / data.get("path", ".")).resolve())
    for split in splits:
        if split not in data or not isinstance(data[split], str):
            raise ValueError(f"Dataset must define a directory for split: {split}")
        if not (Path(data["path"]) / data[split]).is_dir():
            raise FileNotFoundError(f"Missing dataset {split}: {data['path']}/{data[split]}")
    return data


def _class_names(names) -> dict[int, str]:
    return dict(enumerate(names)) if isinstance(names, list) else {int(k): str(v) for k, v in names.items()}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_main():
    parser = argparse.ArgumentParser(description="Detect an image/video/camera with a runtime profile")
    parser.add_argument("--config", type=Path, default=Path("configs/runtime/generic.yaml"))
    parser.add_argument("--weights-dir", type=Path, default=Path("weights"))
    parser.add_argument("--source", required=True, help="image, directory, video or camera index")
    parser.add_argument("--output", type=Path, default=Path("runs/detect"))
    parser.add_argument("--save-images", action="store_true")
    parser.add_argument("--model", help="override model path; relative to weights-dir or absolute")
    parser.add_argument("--device")
    parser.add_argument("--conf", dest="confidence", type=float)
    parser.add_argument("--iou", type=float)
    parser.add_argument("--imgsz", dest="image_size", type=int)
    parser.add_argument("--classes", dest="target_classes", nargs="*",
                        help="exact class names; pass with no values to clear filtering")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Output already exists: {args.output}; choose a new --output directory")
    source = Path(args.source)
    extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    images = None
    if source.is_dir():
        images = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in extensions)
        if not images:
            raise ValueError(f"No images in {source}")
    elif source.suffix.lower() in extensions:
        if not source.is_file():
            raise FileNotFoundError(f"Image not found: {source}")
        images = [source]
    profile = load_profile(args.config)
    overrides = {key: getattr(args, key) for key in (
        "device", "confidence", "iou", "image_size", "target_classes") if getattr(args, key) is not None}
    if args.model is not None:
        overrides["path"] = args.model
    model_config = replace(profile.model, **overrides)
    detector = create_detector(model_config, args.weights_dir)
    import cv2

    args.output.mkdir(parents=True, exist_ok=False)
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
        if images is not None:
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
    parser.add_argument("--batch", type=int)
    parser.add_argument("--imgsz", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--name")
    args = parser.parse_args()
    for key in ("epochs", "imgsz"):
        if getattr(args, key) is not None and getattr(args, key) <= 0:
            parser.error(f"--{key} must be positive")
    if args.batch is not None and args.batch != -1 and args.batch <= 0:
        parser.error("--batch must be positive, or -1 for automatic batch selection")
    if args.workers is not None and args.workers < 0:
        parser.error("--workers must be non-negative")
    settings = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    weights = Path(settings.pop("model")).expanduser()
    if not weights.is_absolute():
        weights = args.weights_dir / weights
    if not weights.is_file():
        raise FileNotFoundError(f"Prepare pretrained weights first: {weights}")
    data_file = (args.config.resolve().parent / settings.pop("data")).resolve()
    data = _dataset_config(data_file, ("train", "val"))
    args.project.mkdir(parents=True, exist_ok=True)
    snapshots = args.project.resolve() / "configs"
    snapshots.mkdir(exist_ok=True)
    snapshot = Path(tempfile.mkdtemp(prefix="train-", dir=snapshots))
    resolved = snapshot / "dataset.yaml"
    resolved.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    for key in ("epochs", "device", "batch", "imgsz", "workers", "name"):
        if getattr(args, key) is not None:
            settings[key] = getattr(args, key)
    metadata = {"model": str(weights.resolve()), "data": str(data_file),
                "resolved_data": str(resolved), "parameters": settings}
    (snapshot / "training.yaml").write_text(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False))
    from ultralytics import YOLO

    model = YOLO(str(weights.resolve()), task="detect")
    model.train(data=str(resolved), project=str(args.project.resolve()), **settings)
    save_dir = Path(model.trainer.save_dir)
    (save_dir / "training_config.yaml").write_text(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False))
    print(f"Best checkpoint (if saved by trainer): {save_dir / 'weights/best.pt'}")


def val_main():
    parser = argparse.ArgumentParser(description="Evaluate a selected model before downstream use")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("configs/datasets/citrus.yaml"))
    parser.add_argument("--output", type=Path, default=Path("runs/val/validation"))
    parser.add_argument("--split", choices=["train", "val", "test"], default="val")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args()
    if args.imgsz <= 0 or args.batch <= 0 or args.workers < 0:
        parser.error("imgsz/batch must be positive and workers non-negative")
    weights = args.weights.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not weights.is_file():
        raise FileNotFoundError(weights)
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}; choose a new --output directory")
    data_file = args.data.expanduser().resolve()
    data = _dataset_config(data_file, (args.split,))
    from ultralytics import YOLO

    model = YOLO(str(weights), task="detect")
    model.overrides["device"] = args.device
    if _class_names(model.names) != _class_names(data["names"]):
        raise ValueError("Model and dataset class mappings differ; evaluate with matching labels")
    output.mkdir(parents=True, exist_ok=False)
    resolved = output / "dataset.yaml"
    resolved.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    parameters = dict(split=args.split, device=args.device, imgsz=args.imgsz, batch=args.batch,
                      workers=args.workers, plots=args.plots)
    metadata = dict(weights=str(weights), weights_sha256=_sha256(weights), data=str(data_file),
                    resolved_data=str(resolved), parameters=parameters)
    (output / "validation_config.yaml").write_text(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False))
    metrics = model.val(data=str(resolved), project=str(output.parent), name=output.name,
                        exist_ok=True, **parameters)
    results = {str(key): float(value) for key, value in metrics.results_dict.items()}
    (output / "metrics.json").write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"Evaluation results: {output / 'metrics.json'}")


def export_main():
    parser = argparse.ArgumentParser(description="Export weights; RKNN conversion is optional and unvalidated")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--format", choices=["onnx", "rknn"], default="onnx")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, help="optional ONNX operator-set version")
    parser.add_argument("--dynamic", action="store_true", help="dynamic ONNX input shapes")
    args = parser.parse_args()
    if args.imgsz <= 0 or (args.opset is not None and args.opset <= 0):
        parser.error("imgsz and opset must be positive")
    if args.format != "onnx" and (args.dynamic or args.opset is not None):
        parser.error("--dynamic and --opset are supported only for ONNX")
    if not args.weights.is_file():
        raise FileNotFoundError(args.weights)
    from ultralytics import YOLO

    options = {"format": args.format, "imgsz": args.imgsz, "simplify": False}
    if args.opset is not None:
        options["opset"] = args.opset
    if args.dynamic:
        options["dynamic"] = True
    if args.format == "rknn":
        options["name"] = "rk3588"
    model = YOLO(str(args.weights.resolve()), task="detect")
    artifact = Path(model.export(**options)).resolve()
    if not artifact.exists():
        raise RuntimeError(f"Exporter did not create the reported artifact: {artifact}")
    manifest = artifact / "export_manifest.json" if artifact.is_dir() else artifact.with_suffix(artifact.suffix + ".json")
    metadata = dict(schema_version=1, format=args.format, artifact=artifact.name,
                    artifact_sha256=_sha256(artifact) if artifact.is_file() else None,
                    source_weights=str(args.weights.resolve()), source_sha256=_sha256(args.weights),
                    requested_image_size=args.imgsz, requested_opset=args.opset, dynamic=args.dynamic,
                    class_names=_class_names(model.names))
    manifest.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(f"Exported model: {artifact}\nModel information: {manifest}")
