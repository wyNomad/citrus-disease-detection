"""Command entry point; install the shared package with pip install -e . first."""

from citrus_vision.cli import train_main


if __name__ == "__main__":
    train_main()
