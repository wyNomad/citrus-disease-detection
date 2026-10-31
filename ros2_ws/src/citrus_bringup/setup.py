from pathlib import Path
import os
from setuptools import find_packages, setup

NAME = "citrus_bringup"
files = [
    ("share/ament_index/resource_index/packages", ["resource/" + NAME]),
    ("share/" + NAME, ["package.xml"]),
]
files.append(("share/" + NAME + "/launch", ["launch/pipeline.launch.py"]))
root = Path(__file__).resolve().parents[3]
for directory in ("runtime", "cameras"):
    files.append(("share/" + NAME + "/configs/" + directory,
                  [os.path.relpath(path, Path(__file__).resolve().parent)
                   for path in sorted((root / "configs" / directory).glob("*.yaml"))]))
setup(
    name=NAME, version="0.1.0", packages=find_packages(exclude=["test"]),
    data_files=files, install_requires=["setuptools"], zip_safe=True,
    maintainer="wyNomad", maintainer_email="175272477+wyNomad@users.noreply.github.com",
    description="Citrus vision ROS 2 adapter", license="LicenseRef-Unspecified",
    entry_points={"console_scripts": []},
)
