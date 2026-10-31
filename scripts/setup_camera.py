"""Fetch the pinned driver or import a matching local v2.7.6 source; never overwrite."""

import argparse
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="optional existing OrbbecSDK_ROS2 v2.7.6 tree")
    parser.add_argument("--destination", type=Path, default=ROOT / "ros2_ws/src/vendor/orbbec")
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    settings = yaml.safe_load((ROOT / "dependencies/orbbec.repos").read_text())["repositories"]["orbbec"]
    if args.source:
        source = args.source.expanduser().resolve()
        if source == destination or source in destination.parents or destination in source.parents:
            raise ValueError("source and destination must not overlap")
        package = source / "orbbec_camera/package.xml"
        if not package.is_file() or ET.parse(package).findtext("version") != "2.7.6":
            raise ValueError("local source must be the Gemini 305-compatible v2.7.6 driver")
        shutil.copytree(source, destination, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    else:
        destination.mkdir(parents=True)
        run("git", "init", cwd=destination)
        run("git", "remote", "add", "origin", settings["url"], cwd=destination)
        run("git", "fetch", "--depth", "1", "origin", settings["version"], cwd=destination)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=destination)
    if not (destination / "orbbec_camera/launch/gemini305.launch.py").is_file():
        raise ValueError("driver lacks gemini305.launch.py")
    patch = str(ROOT / "dependencies/patches/orbbec-pointcloud-row-step.patch")
    check = subprocess.run(["patch", "-p1", "--dry-run", "--batch", "--forward", "-i", patch], cwd=destination,
                           capture_output=True, text=True)
    if check.returncode == 0:
        run("patch", "-p1", "--batch", "--forward", "-i", patch, cwd=destination)
    else:
        reverse = subprocess.run(["patch", "-p1", "--reverse", "--dry-run", "--batch", "-i", patch],
                                 cwd=destination, capture_output=True, text=True)
        if reverse.returncode:
            raise RuntimeError("Driver differs from pinned baseline; inspect before patching: " + check.stderr)
    print(f"Driver prepared: {destination}. Camera and ARM64 runtime remain unvalidated.")


if __name__ == "__main__":
    main()
