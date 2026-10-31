"""Synthetic ROS transport test; needs the built/sourced project overlay, no camera."""

import copy
import math
import time

import numpy as np
import pytest

rclpy = pytest.importorskip("rclpy")
pytest.importorskip("citrus_interfaces.msg")
pytest.importorskip("citrus_detector.node")
from cv_bridge import CvBridge
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo
from citrus_interfaces.msg import Target3DArray
from citrus_detector.node import DetectorNode
from citrus_localizer.node import LocalizerNode
from citrus_vision.types import Detection


@pytest.mark.parametrize("encoding", ["16UC1", "32FC1"])
def test_image_detection_depth_transport_preserves_stamp_and_invalid_targets(tmp_path, monkeypatch, encoding):
    from citrus_detector import node as detector_module

    class FakeDetector:
        def detect(self, image):
            return [Detection(0, "bottle", .9, (1., 1., 3., 3.)),
                    Detection(1, "leaf", .8, (2., 0., 4., 2.))]

    monkeypatch.setattr(detector_module, "create_detector", lambda *args: FakeDetector())
    profile = tmp_path / "test.yaml"
    profile.write_text("model:\n  path: unused.pt\nlocalization:\n  sample_radius: 0\npublish_annotated: true\n")
    log_dir = tmp_path / "ros_logs"
    log_dir.mkdir()
    monkeypatch.setenv("ROS_LOG_DIR", str(log_dir))
    rclpy.init(args=["--ros-args", "-p", f"profile_file:={profile}"])
    detector = localizer = probe = executor = None
    try:
        detector, localizer, probe = DetectorNode(), LocalizerNode(), Node("synthetic_probe")
        executor = SingleThreadedExecutor()
        for node in (detector, localizer, probe):
            executor.add_node(node)
        received, annotated = [], []
        sub = probe.create_subscription(Target3DArray, "/citrus/targets_3d", received.append, 10)
        sub_image = probe.create_subscription(Image, "/citrus/annotated_image", annotated.append, qos_profile_sensor_data)
        color_pub = probe.create_publisher(Image, "/camera/color/image_raw", qos_profile_sensor_data)
        depth_pub = probe.create_publisher(Image, "/camera/depth/image_raw", qos_profile_sensor_data)
        info_pub = probe.create_publisher(CameraInfo, "/camera/color/camera_info", qos_profile_sensor_data)
        bridge = CvBridge()
        color = bridge.cv2_to_imgmsg(np.zeros((4, 4, 3), np.uint8), "bgr8")
        color.header.frame_id = "camera_color_optical_frame"
        data = np.full((4, 4), 1000 if encoding == "16UC1" else 1.,
                       np.uint16 if encoding == "16UC1" else np.float32)
        data[1, 3] = 0
        depth = bridge.cv2_to_imgmsg(data, encoding)
        info = CameraInfo(width=4, height=4, k=[2., 0., 2., 0., 2., 2., 0., 0., 1.])
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and not received:
            color.header.stamp = probe.get_clock().now().to_msg()
            info.header = copy.deepcopy(color.header)
            depth.header = copy.deepcopy(color.header)
            info_pub.publish(info)
            depth_pub.publish(depth)
            color_pub.publish(color)
            for _ in range(10):
                executor.spin_once(timeout_sec=.02)
        assert received, "No localized output received from synthetic ROS pipeline"
        output = received[0]
        assert output.header.frame_id == color.header.frame_id
        assert output.header.stamp == output.depth_stamp
        assert len(output.targets) == 2
        first, second = output.targets
        assert first.depth_valid and first.detection.class_name == "bottle"
        assert (first.position.x, first.position.y, first.position.z) == (0., 0., 1.)
        assert not second.depth_valid and math.isnan(second.position.z)
        assert annotated and annotated[0].header.frame_id == output.header.frame_id
        assert annotated[0].header.stamp == output.header.stamp
    finally:
        if executor is not None:
            executor.shutdown()
        for node in (detector, localizer, probe):
            if node is not None:
                node.destroy_node()
        rclpy.shutdown()
