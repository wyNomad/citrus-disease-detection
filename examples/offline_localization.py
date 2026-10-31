"""Geometry-only demonstration using synthetic depth; no hardware or model required."""

import json
import numpy as np

from citrus_vision.config import LocalizationConfig
from citrus_vision.geometry import Intrinsics, depth_in_metres, sample_depth, deproject


def main():
    settings = LocalizationConfig()
    depth = depth_in_metres(np.full((480, 640), 1000, dtype=np.uint16), "16UC1", settings.depth_scale)
    camera = Intrinsics(640, 480, 600, 600, 320, 240)
    u, v = 380.0, 240.0
    z = sample_depth(depth, u, v, settings)
    print(json.dumps({"synthetic": True, "pixel": [u, v],
                      "position_metres": deproject(u, v, z, camera)}, indent=2))


if __name__ == "__main__":
    main()
