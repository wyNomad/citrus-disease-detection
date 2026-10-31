"""Compatibility entry point; install the shared package with pip install -e . first."""

from citrus_vision.cli import export_main


if __name__ == "__main__":
    export_main()
