from pathlib import Path
from setuptools import find_packages, setup

NAME = "citrus_detector"
files = [
    ("share/ament_index/resource_index/packages", ["resource/" + NAME]),
    ("share/" + NAME, ["package.xml"]),
]
setup(
    name=NAME, version="0.1.0", packages=find_packages(exclude=["test"]),
    data_files=files, install_requires=["setuptools"], zip_safe=True,
    maintainer="wyNomad", maintainer_email="175272477+wyNomad@users.noreply.github.com",
    description="Citrus vision ROS 2 adapter", license="LicenseRef-Unspecified",
    entry_points={"console_scripts": ['detector = citrus_detector.node:main']},
)
