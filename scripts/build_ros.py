"""Build with the current Python so ROS node executables see this environment."""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-only", action="store_true", help="skip third-party camera packages")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    if os.environ.get("ROS_DISTRO") != "humble":
        parser.error("source /opt/ros/humble/setup.bash first")
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-c", "from colcon_core.command import main; raise SystemExit(main())",
               "--log-base", str(root / "ros2_ws/log"), "build",
               "--base-paths", str(root / "ros2_ws/src"),
               "--build-base", str(root / "ros2_ws/build"),
               "--install-base", str(root / "ros2_ws/install"), "--symlink-install",
               "--parallel-workers", str(args.workers)]
    if args.core_only:
        command.extend(["--packages-select", "citrus_vision", "citrus_interfaces", "citrus_detector",
                        "citrus_localizer", "citrus_bringup"])
    command.extend(["--cmake-args", f"-DPython3_EXECUTABLE={sys.executable}"])
    subprocess.run(command, cwd=root, check=True)


if __name__ == "__main__":
    main()
