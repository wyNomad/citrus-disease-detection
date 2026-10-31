"""Synchronize detections with aligned depth; cache matching color calibration."""

import copy
import math

from cv_bridge import CvBridge
import message_filters
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from citrus_interfaces.msg import Detection2DArray, Target3D, Target3DArray

from citrus_vision.config import load_profile
from citrus_vision.geometry import Intrinsics, depth_in_metres, sample_depth, deproject


class LocalizerNode(Node):
    def __init__(self):
        super().__init__("citrus_localizer")
        self.declare_parameter("profile_file", "")
        self.profile = load_profile(self.get_parameter("profile_file").value)
        self.bridge = CvBridge()
        self.camera_info = None
        self.info_sub = self.create_subscription(
            CameraInfo, self.profile.topics.camera_info, self.on_info, qos_profile_sensor_data)
        self.detections_sub = message_filters.Subscriber(
            self, Detection2DArray, self.profile.topics.detections, qos_profile=qos_profile_sensor_data)
        self.depth_sub = message_filters.Subscriber(
            self, Image, self.profile.topics.depth, qos_profile=qos_profile_sensor_data)
        settings = self.profile.localization
        self.synchronizer = message_filters.ApproximateTimeSynchronizer(
            [self.detections_sub, self.depth_sub], settings.sync_queue, settings.sync_slop)
        self.synchronizer.registerCallback(self.on_pair)
        self.publisher = self.create_publisher(Target3DArray, self.profile.topics.targets, 10)
        self.get_logger().info("Localizer ready; waiting for aligned depth and color calibration")

    def on_info(self, message):
        self.camera_info = message

    def on_pair(self, detections, depth):
        info = self.camera_info
        try:
            if info is None:
                raise ValueError("waiting for color CameraInfo")
            if not detections.header.frame_id or detections.header.frame_id != info.header.frame_id:
                raise ValueError("detections and color calibration must use the same optical frame")
            if depth.header.frame_id != info.header.frame_id:
                raise ValueError("depth must be registered to the color optical frame")
            expected = (info.width, info.height)
            if (detections.image_width, detections.image_height) != expected or (depth.width, depth.height) != expected:
                raise ValueError("color, aligned depth and CameraInfo sizes differ; verify depth_registration")
            if info.binning_x > 1 or info.binning_y > 1 or info.roi.x_offset or info.roi.y_offset:
                raise ValueError("binned/cropped calibration is not supported")
            if info.roi.width not in (0, info.width) or info.roi.height not in (0, info.height):
                raise ValueError("partial calibration ROI is not supported")
            intrinsics = Intrinsics(info.width, info.height, info.k[0], info.k[4], info.k[2], info.k[5],
                                    tuple(info.d), info.distortion_model)
            array = self.bridge.imgmsg_to_cv2(depth, desired_encoding="passthrough")
            metres = depth_in_metres(array, depth.encoding, self.profile.localization.depth_scale)
            result = Target3DArray()
            result.header = copy.deepcopy(detections.header)
            result.depth_stamp = copy.deepcopy(depth.header.stamp)
            for index, detection in enumerate(detections.detections):
                item = Target3D()
                item.detection_index = index
                item.detection = copy.deepcopy(detection)
                item.position.x = item.position.y = item.position.z = math.nan
                z = sample_depth(metres, detection.center_u, detection.center_v, self.profile.localization)
                item.depth_valid = z is not None
                item.status = "valid" if item.depth_valid else "invalid_depth_or_pixel"
                if item.depth_valid:
                    item.position.x, item.position.y, item.position.z = deproject(
                        detection.center_u, detection.center_v, z, intrinsics)
                result.targets.append(item)
            self.publisher.publish(result)
        except Exception as exc:
            self.get_logger().warning(f"Localization skipped: {exc}", throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = LocalizerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
