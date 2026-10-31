"""Image -> stamped detections. Single callback, depth-one input queue."""

import copy

from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from citrus_interfaces.msg import Detection2D, Detection2DArray

from citrus_vision.config import load_profile
from citrus_vision.inference import create_detector


class DetectorNode(Node):
    def __init__(self):
        super().__init__("citrus_detector")
        self.declare_parameter("profile_file", "")
        self.declare_parameter("weights_dir", "weights")
        self.profile = load_profile(self.get_parameter("profile_file").value)
        self.detector = create_detector(self.profile.model, self.get_parameter("weights_dir").value)
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Detection2DArray, self.profile.topics.detections, 10)
        self.annotated = self.create_publisher(Image, self.profile.topics.annotated, qos_profile_sensor_data)
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.subscription = self.create_subscription(Image, self.profile.topics.image, self.on_image, qos)
        self.get_logger().info(f"Detector ready: {self.profile.model.path}; backend={self.profile.model.backend}")

    def on_image(self, message):
        try:
            frame = self.bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
            detections = self.detector.detect(frame)
            result = Detection2DArray()
            result.header = copy.deepcopy(message.header)
            result.image_width, result.image_height = message.width, message.height
            for detection in detections:
                item = Detection2D()
                item.class_id, item.class_name = detection.class_id, detection.class_name
                item.confidence = detection.confidence
                item.xyxy = list(detection.xyxy)
                item.center_u, item.center_v = detection.center
                result.detections.append(item)
            self.publisher.publish(result)
            if self.profile.publish_annotated:
                import cv2

                frame = frame.copy()
                for detection in detections:
                    x1, y1, x2, y2 = map(int, detection.xyxy)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, detection.class_name, (x1, max(15, y1-5)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                annotated = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
                annotated.header = copy.deepcopy(message.header)
                self.annotated.publish(annotated)
        except Exception as exc:
            self.get_logger().error(f"Detection failed: {exc}", throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = DetectorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
