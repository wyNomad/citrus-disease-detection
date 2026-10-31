"""Load a runtime profile; relative weights are rooted at an explicit model directory."""

from dataclasses import dataclass, field
from pathlib import Path
import math

import yaml


@dataclass(frozen=True)
class ModelConfig:
    path: str
    backend: str = "ultralytics"
    device: str = "cpu"
    confidence: float = 0.25
    iou: float = 0.45
    image_size: int = 640
    target_classes: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.path or not isinstance(self.path, str):
            raise ValueError("model.path must be a non-empty string")
        if not 0 <= self.confidence <= 1 or not 0 <= self.iou <= 1:
            raise ValueError("confidence and iou must be in [0, 1]")
        if type(self.image_size) is not int or self.image_size <= 0:
            raise ValueError("image_size must be a positive integer")
        if not isinstance(self.target_classes, list) or any(
            not isinstance(name, str) for name in self.target_classes
        ):
            raise ValueError("target_classes must be a list of class names")


@dataclass(frozen=True)
class LocalizationConfig:
    depth_scale: float = 0.001
    min_depth: float = 0.1
    max_depth: float = 10.0
    sample_radius: int = 2
    sync_slop: float = 0.04
    sync_queue: int = 30

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (
            self.depth_scale, self.min_depth, self.max_depth, self.sync_slop
        )):
            raise ValueError("localization values must be finite")
        if self.depth_scale <= 0 or not 0 <= self.min_depth < self.max_depth:
            raise ValueError("invalid depth scale or depth limits")
        if type(self.sample_radius) is not int or not 0 <= self.sample_radius <= 20:
            raise ValueError("sample_radius must be an integer in [0, 20]")
        if type(self.sync_queue) is not int or self.sync_queue < 1 or self.sync_slop <= 0:
            raise ValueError("sync_queue and sync_slop must be positive")


@dataclass(frozen=True)
class Topics:
    image: str = "/camera/color/image_raw"
    depth: str = "/camera/depth/image_raw"
    camera_info: str = "/camera/color/camera_info"
    detections: str = "/citrus/detections"
    targets: str = "/citrus/targets_3d"
    annotated: str = "/citrus/annotated_image"

    def __post_init__(self):
        if any(not isinstance(v, str) or not v for v in vars(self).values()):
            raise ValueError("topic names must be non-empty strings")


@dataclass(frozen=True)
class RuntimeProfile:
    model: ModelConfig
    localization: LocalizationConfig = field(default_factory=LocalizationConfig)
    topics: Topics = field(default_factory=Topics)
    publish_annotated: bool = False


def load_profile(path: str | Path) -> RuntimeProfile:
    with Path(path).expanduser().open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict) or "model" not in data:
        raise ValueError("runtime profile must contain a model mapping")
    unknown = set(data) - {"model", "localization", "topics", "publish_annotated"}
    if unknown:
        raise ValueError(f"unknown profile keys: {sorted(unknown)}")
    annotated = data.get("publish_annotated", False)
    if type(annotated) is not bool:
        raise ValueError("publish_annotated must be a YAML boolean")
    return RuntimeProfile(
        model=ModelConfig(**data["model"]),
        localization=LocalizationConfig(**data.get("localization", {})),
        topics=Topics(**data.get("topics", {})),
        publish_annotated=annotated,
    )


def resolve_model_path(model: ModelConfig, weights_dir: str | Path) -> Path:
    path = Path(model.path).expanduser()
    if not path.is_absolute():
        path = Path(weights_dir).expanduser() / path
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}. Prepare weights first; no automatic download.")
    return path
