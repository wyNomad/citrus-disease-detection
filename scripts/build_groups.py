"""Command entry point; install the shared package with pip install -e . first."""

from citrus_vision.dataset import build_groups_main


if __name__ == "__main__":
    build_groups_main()
