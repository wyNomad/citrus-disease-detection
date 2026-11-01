"""The same detector is used by offline tools and ROS adapters."""

from pathlib import Path
from typing import Protocol

from .config import ModelConfig, resolve_model_path
from .types import Detection


class Detector(Protocol):
    def detect(self, image) -> list[Detection]:
        """Return boxes in original image coordinates, before resize/letterbox."""
        ...


class UltralyticsDetector:
    def __init__(self, config: ModelConfig, weights_dir: str | Path):
        model_path = resolve_model_path(config, weights_dir)
        from ultralytics import YOLO

        self.model = YOLO(str(model_path), task="detect")
        self.config = config
        # Export-format class metadata may initialize a backend before predict().
        self.model.overrides["device"] = config.device
        names = self.model.names
        self.names = dict(enumerate(names)) if isinstance(names, list) else names
        requested = set(config.target_classes)
        missing = requested - set(self.names.values())
        if missing:
            raise ValueError(f"Classes not present in model: {sorted(missing)}")
        self.class_ids = [key for key, name in self.names.items() if name in requested]

    def detect(self, image) -> list[Detection]:
        results = self.model.predict(
            source=image, conf=self.config.confidence, iou=self.config.iou,
            imgsz=self.config.image_size, device=self.config.device,
            classes=self.class_ids or None, verbose=False, save=False,
        )
        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls.item())
                detections.append(Detection(
                    class_id, self.names[class_id], float(box.conf.item()),
                    tuple(float(value) for value in box.xyxy[0].tolist()),
                ))
        return detections


def create_detector(config: ModelConfig, weights_dir: str | Path) -> Detector:
    if config.backend == "ultralytics":
        return UltralyticsDetector(config, weights_dir)
    if config.backend == "rknn":
        raise NotImplementedError(
            "RK3588 backend is reserved, not board-validated or implemented yet. "
            "See docs/DEPLOYMENT.md; laptop baseline uses backend: ultralytics."
        )
    raise ValueError(f"Unknown inference backend: {config.backend}")
