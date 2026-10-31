import copy

import numpy as np
import pytest

rclpy = pytest.importorskip("rclpy")
pytest.importorskip("citrus_localizer.node")
from cv_bridge import CvBridge
from sensor_msgs.msg import CameraInfo
from citrus_interfaces.msg import Detection2D, Detection2DArray
from citrus_localizer.node import LocalizerNode


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    config = tmp_path / "profile.yaml"
    config.write_text("model:\n  path: unused.pt\nlocalization:\n  sample_radius: 0\n")
    monkeypatch.setenv("ROS_LOG_DIR", str(tmp_path / "logs"))
    rclpy.init(args=["--ros-args", "-p", f"profile_file:={config}"])
    node = LocalizerNode()
    received = []
    node.publisher = type("Capture", (), {"publish": lambda self, msg: received.append(msg)})()
    info = CameraInfo(width=4, height=4, k=[2., 0., 2., 0., 2., 2., 0., 0., 1.])
    info.header.frame_id = "camera_color_optical_frame"
    node.on_info(info)
    detections = Detection2DArray(image_width=4, image_height=4)
    detections.header = copy.deepcopy(info.header)
    detections.header.stamp.sec = 10
    detections.detections = [Detection2D(class_id=0, class_name="bottle", confidence=.9,
                                       center_u=2., center_v=2.)]
    depth = CvBridge().cv2_to_imgmsg(np.full((4, 4), 1000, np.uint16), "16UC1")
    depth.header = copy.deepcopy(detections.header)
    try:
        yield node, detections, depth, received
    finally:
        node.destroy_node()
        rclpy.shutdown()


@pytest.mark.parametrize("frame", ["camera_depth_optical_frame", "another_camera_optical_frame", ""])
def test_unregistered_or_foreign_depth_frames_are_rejected(pipeline, frame):
    node, detections, depth, received = pipeline
    depth.header.frame_id = frame
    node.on_pair(detections, depth)
    assert not received


@pytest.mark.parametrize("invalid", ["missing_info", "wrong_size", "zero_focal", "cropped_info"])
def test_invalid_calibration_does_not_produce_coordinates(pipeline, invalid):
    node, detections, depth, received = pipeline
    if invalid == "missing_info":
        node.camera_info = None
    elif invalid == "wrong_size":
        detections.image_width = 5
    elif invalid == "zero_focal":
        node.camera_info.k[0] = 0.
    else:
        node.camera_info.roi.x_offset = 1
    node.on_pair(detections, depth)
    assert not received


def test_synchronizer_rejects_stale_depth_and_accepts_matching_depth(pipeline):
    node, detections, depth, received = pipeline
    depth.header.stamp.sec = 11
    node.detections_sub.signalMessage(detections)
    node.depth_sub.signalMessage(depth)
    assert not received
    depth.header.stamp = copy.deepcopy(detections.header.stamp)
    node.depth_sub.signalMessage(depth)
    assert len(received) == 1
    assert received[0].header.stamp == received[0].depth_stamp


def test_empty_detections_publish_empty_result(pipeline):
    node, detections, depth, received = pipeline
    detections.detections = []
    node.on_pair(detections, depth)
    assert len(received) == 1 and not received[0].targets
