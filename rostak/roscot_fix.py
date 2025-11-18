import rclpy
from rclpy.node import Node
from rostak.cot_utility import CotUtility
from std_msgs.msg import String
from sensor_msgs.msg import NavSatFix
from rclpy.executors import SingleThreadedExecutor

class RosCotFix(Node):

    def __init__(self) -> None:
        super().__init__("rostak_fix")
        self.declare_parameter("cot_params","./")
        config_path = self.get_parameter("cot_params").value
        self.util_ = CotUtility(config_path)
        
        self.declare_parameter("rate", 0.2)
        self.rate_ = self.get_parameter("rate").value

        self.msg_ = String()

        self.pub_ = self.create_publisher(String, "tak_tx", 1)

        self.create_subscription(NavSatFix, "fix", self.fix_callback, 1)
        #self.get_logger().info(self.util_.get_config())

    def fix_callback(self, msg : NavSatFix) -> None:
        """Generate a status COT event"""
        self.util_.set_point(msg)
        stale_in = 2 * max(1, 1 / self.rate_)
        self.msg_.data = self.util_.new_status_msg(stale_in)
        self.pub_.publish(self.msg)

def main(args=None) -> None:
    rclpy.init()
    fix = RosCotFix()
    
    executor = SingleThreadedExecutor()
    executor.add_node(fix)

    try:
        executor.spin()
    finally:
        executor.shutdown()
        fix.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
