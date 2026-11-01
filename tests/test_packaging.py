from importlib.metadata import distribution


def test_core_distribution_keeps_its_metadata_when_ros_overlay_is_loaded():
    core = distribution("citrus-vision-core")
    assert core.metadata["Name"] == "citrus-vision-core"
    assert "inference" in core.metadata.get_all("Provides-Extra", [])
    commands = {entry.name for entry in core.entry_points if entry.group == "console_scripts"}
    assert {"citrus-train", "citrus-val", "citrus-detect", "citrus-export", "citrus-prepare-data"} <= commands
    assert any(requirement.startswith("ultralytics") for requirement in core.requires)
