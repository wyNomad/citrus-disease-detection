from setuptools import find_packages, setup

setup(
    name="citrus_vision", version="0.1.0", packages=find_packages(),
    data_files=[("share/ament_index/resource_index/packages", ["resource/citrus_vision"]),
                ("share/citrus_vision", ["package.xml"])],
    install_requires=["setuptools"], zip_safe=True,
    maintainer="wyNomad", maintainer_email="175272477+wyNomad@users.noreply.github.com",
    description="ROS packaging of the same shared citrus_vision Python source",
    license="LicenseRef-Unspecified",
)
