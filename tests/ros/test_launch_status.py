import importlib.util
from pathlib import Path
import sys

import pytest

pytest.importorskip("launch_ros")
from launch import LaunchDescription, LaunchService
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit


FILE = Path(__file__).resolve().parents[2] / "ros2_ws/src/citrus_bringup/launch/pipeline.launch.py"
SPEC = importlib.util.spec_from_file_location("citrus_pipeline_launch", FILE)
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


@pytest.mark.parametrize("code,expected", [(0, 0), (1, 1), (7, 1)])
def test_child_failure_is_reflected_in_launch_exit_status(tmp_path, monkeypatch, code, expected):
    monkeypatch.setenv("ROS_LOG_DIR", str(tmp_path / "logs"))
    process = ExecuteProcess(cmd=[sys.executable, "-c", f"raise SystemExit({code})"], output="log")
    service = LaunchService()
    service.include_launch_description(LaunchDescription([
        RegisterEventHandler(OnProcessExit(target_action=process, on_exit=PIPELINE.pipeline_process_exit)),
        process,
    ]))
    assert service.run() == expected
