"""RGB-D optical coordinates. Units: pixels in, metres out; x right, y down, z forward."""

from dataclasses import dataclass
import math

import numpy as np

from .config import LocalizationConfig


@dataclass(frozen=True)
class Intrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    distortion: tuple[float, ...] = ()
    distortion_model: str = "plumb_bob"

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("invalid calibration image size")
        if not all(math.isfinite(v) for v in (self.fx, self.fy, self.cx, self.cy, *self.distortion)):
            raise ValueError("calibration values must be finite")
        if self.fx <= 0 or self.fy <= 0:
            raise ValueError("camera is uncalibrated: fx/fy must be positive")


def depth_in_metres(depth, encoding: str, scale: float) -> np.ndarray:
    array = np.asarray(depth)
    if array.ndim != 2:
        raise ValueError("depth image must have one channel")
    if encoding == "16UC1":
        if array.dtype.kind != "u" or array.dtype.itemsize != 2:
            raise ValueError("16UC1 requires uint16 data")
        return array.astype(np.float64) * scale
    if encoding == "32FC1":
        if array.dtype.kind != "f" or array.dtype.itemsize != 4:
            raise ValueError("32FC1 requires float32 data")
        return array.astype(np.float64)  # REP-118: float depth already in metres
    raise ValueError(f"unsupported depth encoding: {encoding}")


def sample_depth(depth_m, u: float, v: float, config: LocalizationConfig) -> float | None:
    height, width = depth_m.shape
    if not math.isfinite(u) or not math.isfinite(v) or not (0 <= u < width and 0 <= v < height):
        return None
    x, y = int(u), int(v)
    radius = config.sample_radius
    patch = depth_m[max(0, y-radius):min(height, y+radius+1),
                    max(0, x-radius):min(width, x+radius+1)]
    valid = patch[np.isfinite(patch) & (patch > config.min_depth) & (patch < config.max_depth)]
    return float(np.median(valid)) if valid.size else None


def deproject(u: float, v: float, z: float, intrinsics: Intrinsics) -> tuple[float, float, float]:
    if not all(math.isfinite(value) for value in (u, v, z)) or z <= 0:
        raise ValueError("pixel/depth values must be finite and depth positive")
    if any(intrinsics.distortion):
        import cv2

        matrix = np.array([[intrinsics.fx, 0, intrinsics.cx],
                           [0, intrinsics.fy, intrinsics.cy], [0, 0, 1]], dtype=np.float64)
        point = np.array([[[u, v]]], dtype=np.float64)
        coeffs = np.array(intrinsics.distortion, dtype=np.float64)
        if intrinsics.distortion_model in ("plumb_bob", "rational_polynomial"):
            ray = cv2.undistortPoints(point, matrix, coeffs).reshape(2)
        elif intrinsics.distortion_model == "equidistant":
            ray = cv2.fisheye.undistortPoints(point, matrix, coeffs).reshape(2)
        else:
            raise ValueError(f"unsupported distortion model: {intrinsics.distortion_model}")
        return float(ray[0] * z), float(ray[1] * z), float(z)
    return (u - intrinsics.cx) * z / intrinsics.fx, (v - intrinsics.cy) * z / intrinsics.fy, float(z)
