"""Legacy pixel-coordinate adapter; new code should use citrus_vision.inference."""
from pathlib import Path
from citrus_vision.config import load_profile
from citrus_vision.inference import create_detector


class GraspDetector:
    def __init__(self, model_path=None, config="configs/runtime/citrus.yaml", weights_dir="weights"):
        from dataclasses import replace
        profile = load_profile(config)
        model = profile.model
        if model_path is not None:
            model = replace(model, path=str(Path(model_path).resolve()))
        self.detector = create_detector(model, weights_dir)

    def get_target_coordinate(self, image_path_or_frame):
        detections = self.detector.detect(image_path_or_frame)
        if not detections:
            return False, None
        best = max(detections, key=lambda d: d.confidence)
        x, y = best.center
        x1, y1, x2, y2 = best.xyxy
        return True, dict(name=best.class_name, confidence=best.confidence,
                          x=x, y=y, w=x2-x1, h=y2-y1)
