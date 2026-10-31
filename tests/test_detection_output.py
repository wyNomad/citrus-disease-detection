import sys

import pytest

from citrus_vision.cli import detect_main


def test_failed_detection_cannot_truncate_existing_output(tmp_path, monkeypatch):
    output = tmp_path / "existing"
    output.mkdir()
    results = output / "detections.jsonl"
    results.write_text("previous experiment\n")
    image = output / "frame_000000.jpg"
    image.write_bytes(b"keep previous image")
    monkeypatch.setattr(sys, "argv", ["detect", "--source", str(tmp_path / "missing.jpg"),
                                    "--output", str(output)])
    with pytest.raises(FileExistsError, match="choose a new"):
        detect_main()
    assert results.read_text() == "previous experiment\n"
    assert image.read_bytes() == b"keep previous image"


def test_missing_image_does_not_create_output(tmp_path, monkeypatch):
    output = tmp_path / "new"
    monkeypatch.setattr(sys, "argv", ["detect", "--source", str(tmp_path / "missing.jpg"),
                                    "--output", str(output)])
    with pytest.raises(FileNotFoundError, match="Image not found"):
        detect_main()
    assert not output.exists()
