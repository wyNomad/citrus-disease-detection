"""Command entry point; install the shared package with pip install -e . first."""

from citrus_vision.cli import detect_main


if __name__ == "__main__":
    detect_main()
