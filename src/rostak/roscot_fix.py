"""Convert sensor_msgs/NavSatFix into CoT events on tak_tx."""
import os
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from ament_index_python.packages import get_package_share_directory
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import String
from rostak.cot_utility import CotUtility


class RosCotFix(Node):
    def __init__(self):
        super().__init__('roscot_fix')
        default_config = os.path.join(get_package_share_directory('rostak'), 'config', 'cot.yaml')
        config = self.declare_parameter('cot_params', default_config).value
        self.util = CotUtility(config)
        self.stale_seconds = self.declare_parameter('stale_seconds', 300.0).value
        self.tx = self.create_publisher(String, 'tak_tx', 10)
        self.subscription = self.create_subscription(
            NavSatFix, 'fix', self.fix_callback, qos_profile_sensor_data)
        self.get_logger().info(f'GPS → CoT: {self.util.callsign}')

    def fix_callback(self, msg):
        try:
            self.util.set_point(msg)
            self.tx.publish(String(data=self.util.new_status_msg(self.stale_seconds)))
            self.get_logger().info(f'Published {self.util.callsign}: {msg.latitude}, {msg.longitude}')
        except ValueError as exc:
            self.get_logger().warning(f'Ignoring invalid GPS fix: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = RosCotFix()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
