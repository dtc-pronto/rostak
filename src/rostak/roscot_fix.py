"""
import rospy
from rostak.cot_utility import CotUtility
from std_msgs.msg import String
from sensor_msgs.msg import NavSatFix

class RosCotFix:
    def __init__(self):
        rospy.init_node("roscot_fix")
        config_path = rospy.get_param('~cot_params')
        self.util = CotUtility(config_path)
        self.rate = rospy.get_param('~rate', 0.2)
        self.tx = rospy.Publisher('tak_tx', String, queue_size=1)
        self.msg = String()
        rospy.Subscriber("fix", NavSatFix, self.publish_fix)
        rospy.loginfo(self.util.get_config())

    def publish_fix(self, msg):
        """Generate a status COT Event."""
        self.util.set_point(msg)
        stale_in = 2 * max(1, 1 / self.rate)
        self.msg.data = self.util.new_status_msg(stale_in)
        self.tx.publish(self.msg)

if __name__ == '__main__':
    RosCotFix()
    rospy.spin()
"""
import rclpy
from rclpy.node import Node
from rostak.cot_utility import CotUtility
from std_msgs.msg import String
from sensor_msgs.msg import NavSatFix

class RosCotFix(Node):

    def __init__(self) -> None:
        self.declare_parameter("cot_params","./")
        config_path = self.get_parameter("cot_params").value
        self.util_ = CotUtility(config_path)
        
        self.declare_parameter("rate", 0.2)
        self.rate_ = self.get_parameter("rate").value

        self.msg_ = String()

        self.pub_ = self.create_publisher(String, "tak_tx", 1)

        self.create_subscription(NavSatFix, "fix", self.fix_callback)
        self.get_logger().info(self.util_.get_config())

    def fix_callback(msg : NavSatFix) -> None:
        """Generate a status COT event"""
        self.util_.set_point(msg)
        stale_in = 2 * max(1, 1 / self.rate_)
        self.msg_.data = self.util_.new_status_msg(stale_in)
        self.pub_.publish(self.msg)
