"""Portable color/depth -> detections -> optical coordinates pipeline."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml

from citrus_vision.config import load_profile, resolve_model_path


def launch_nodes(context):
    share = Path(get_package_share_directory("citrus_bringup"))
    profile = LaunchConfiguration("profile").perform(context)
    if profile not in {"generic", "citrus"}:
        raise ValueError("profile must be generic or citrus; custom profiles use profile_file")
    custom = LaunchConfiguration("profile_file").perform(context)
    profile_file = str(Path(custom).expanduser().resolve()) if custom else str(share / "configs/runtime" / f"{profile}.yaml")
    weights_dir = str(Path(LaunchConfiguration("weights_dir").perform(context)).expanduser().resolve())
    settings = load_profile(profile_file)
    resolve_model_path(settings.model, weights_dir)
    if settings.model.backend != "ultralytics":
        raise ValueError("Only the ultralytics backend is implemented; RKNN awaits board integration")
    nodes = []
    if LaunchConfiguration("start_camera").perform(context).lower() == "true":
        camera_file = Path(LaunchConfiguration("camera_file").perform(context)).expanduser()
        camera = yaml.safe_load(camera_file.read_text(encoding="utf-8"))["launch_arguments"]
        arguments = {key: str(value) for key, value in camera.items()}
        if arguments.get("depth_registration", "").lower() != "true" or arguments.get("align_target_stream") != "COLOR":
            raise ValueError("localization requires depth registered to COLOR")
        driver = Path(get_package_share_directory("orbbec_camera")) / "launch/gemini305.launch.py"
        nodes.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(driver)), launch_arguments=arguments.items()))
    detector = Node(package="citrus_detector", executable="detector", output="screen",
                    parameters=[{"profile_file": profile_file, "weights_dir": weights_dir}])
    localizer = Node(package="citrus_localizer", executable="localizer", output="screen",
                     parameters=[{"profile_file": profile_file}])
    for process in (detector, localizer):
        nodes.append(RegisterEventHandler(OnProcessExit(
            target_action=process, on_exit=[EmitEvent(event=Shutdown(reason="Pipeline node exited"))])))
    nodes.extend([detector, localizer])
    return nodes


def generate_launch_description():
    share = Path(get_package_share_directory("citrus_bringup"))
    return LaunchDescription([
        DeclareLaunchArgument("profile", default_value="generic"),
        DeclareLaunchArgument("profile_file", default_value=""),
        DeclareLaunchArgument("weights_dir", default_value=str(Path.cwd() / "weights")),
        DeclareLaunchArgument("camera_file", default_value=str(share / "configs/cameras/gemini305.yaml")),
        DeclareLaunchArgument("start_camera", default_value="true", choices=["true", "false"]),
        OpaqueFunction(function=launch_nodes),
    ])
