
import asyncio
import pytak
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from configparser import ConfigParser

class RosTakBridge(Node):
    """
    Proxy CoT messages (xml strings) between ROS and TAK agents.
    """

    def __init__(self):
        super().__init__('rostak_bridge')
        
        # Declare parameters
        self.declare_parameter('COT_URL', '')
        self.declare_parameter('PYTAK_TLS_CLIENT_CERT', '')
        self.declare_parameter('PYTAK_TLS_CLIENT_KEY', '')
        self.declare_parameter('PYTAK_TLS_CLIENT_CAFILE', '')
        self.declare_parameter('PYTAK_TLS_CLIENT_CIPHERS', '')
        self.declare_parameter('PYTAK_TLS_DONT_VERIFY', '')
        self.declare_parameter('PYTAK_TLS_DONT_CHECK_HOSTNAME', '')
        
        # Configure pytak
        self.config = ConfigParser()['DEFAULT']
        self.config["COT_URL"] = self.get_parameter('COT_URL').value
        self.config["PYTAK_TLS_CLIENT_CERT"] = self.get_parameter('PYTAK_TLS_CLIENT_CERT').value
        self.config["PYTAK_TLS_CLIENT_KEY"] = self.get_parameter('PYTAK_TLS_CLIENT_KEY').value
        self.config["PYTAK_TLS_CLIENT_CAFILE"] = self.get_parameter('PYTAK_TLS_CLIENT_CAFILE').value
        self.config["PYTAK_TLS_CLIENT_CIPHERS"] = self.get_parameter('PYTAK_TLS_CLIENT_CIPHERS').value
        self.config["PYTAK_TLS_DONT_VERIFY"] = self.get_parameter('PYTAK_TLS_DONT_VERIFY').value
        self.config["PYTAK_TLS_DONT_CHECK_HOSTNAME"] = self.get_parameter('PYTAK_TLS_DONT_CHECK_HOSTNAME').value
        
    async def run(self):
        # connect to tak server
        try:
            rx_proto, tx_proto = await pytak.protocol_factory(self.config)
        except:
            raise ValueError('TAK url must be valid')

        # bridge objects
        tasks = []
        if tx_proto:
            tx_queue = asyncio.Queue()
            tasks.append(asyncio.create_task(pytak.TXWorker(tx_queue, self.config, tx_proto).run()))
            tasks.append(asyncio.create_task(RosCotWorker(tx_queue, self.config, self).run()))

        if rx_proto:
            rx_queue = asyncio.Queue()
            tasks.append(asyncio.create_task(RosTakReceiver(rx_queue, self.config, rx_proto, self).run()))

        # start workers, restart on error
        while True:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                print(f"[RosTakBridge] Task Completed: {task}")
    
class RosCotWorker(pytak.QueueWorker):
    """
    listen for CoT from ROS and enqueue for TAK
    """
    def __init__(self, queue: asyncio.Queue, config: dict, node: Node) -> None:
        super().__init__(queue, config)
        self.node = node
        self.aio = asyncio.get_event_loop()

    def queue_cotmsg(self, cotmsg):
        self.aio.create_task(
            self.put_queue(cotmsg.data.encode('utf-8'))
        )
    
    async def run(self):
        self.node.get_logger().info(" *** Subscribing to tak_tx ***")
        self.node.create_subscription(String, "tak_tx", self.queue_cotmsg, 10)
        # Keep async worker running so ROS callback threading continues
        while rclpy.ok():
            await asyncio.sleep(0.25)
    
class RosTakReceiver(pytak.RXWorker):
    """
    receive CoT from TAK and publish to ROS
    """
    def __init__(self, queue: asyncio.Queue, config: dict, reader: asyncio.Protocol, node: Node) -> None:
        super().__init__(queue, config, reader)
        self.node = node

    async def run(self):
        pub = self.node.create_publisher(String, 'tak_rx', 10)
        msg = String()
        self.node.get_logger().info(" *** Publishing on tak_rx ***")
        while rclpy.ok():
            cot = await self.reader.readuntil(separator=b'</event>')
            msg.data = cot.decode()
            pub.publish(msg)

async def main_async():
    rclpy.init()
    bridge = RosTakBridge()
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        pass
    finally:
        bridge.destroy_node()
        rclpy.shutdown()

def main(): 
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
