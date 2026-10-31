"""Install the built core wheel in a clean venv outside the source checkout."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import venv


def main():
    root = Path(__file__).resolve().parents[2]
    wheels = list((root / "dist").glob("citrus_vision_core-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Build exactly one core wheel in dist before this check")
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="citrus-wheel-") as temporary:
        directory = Path(temporary)
        venv.EnvBuilder(with_pip=True).create(directory / "venv")
        python = str(directory / "venv/bin/python")
        subprocess.run([python, "-m", "pip", "install", str(wheels[0])],
                       cwd=directory, env=environment, check=True)
        subprocess.run([python, "-c", "from importlib.metadata import distribution; "
                        "from citrus_vision.cli import detect_main; "
                        "d=distribution('citrus-vision-core'); "
                        "assert 'inference' in d.metadata.get_all('Provides-Extra'); "
                        "assert len(d.entry_points)==4; print('Installed core wheel metadata and imports passed')"],
                       cwd=directory, env=environment, check=True)
        subprocess.run([str(directory / "venv/bin/citrus-detect"), "--help"],
                       cwd=directory, env=environment, check=True)


if __name__ == "__main__":
    main()
