"""ROS 2 CoT XML over streaming TCP/TLS, direct-to-ATAK TCP, or UDP.

ROS callbacks run on the ROS executor; network I/O uses a separate thread.
Stream transports reconnect without restarting ROS. No PyTAK version dependency.
"""
import queue
import socket
import ssl
import threading
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class RosTakBridge(Node):
    def __init__(self):
        super().__init__('rostak_bridge')
        self.url = self.declare_parameter('COT_URL', 'udp://127.0.0.1:16969').value
        self.cert = self.declare_parameter('PYTAK_TLS_CLIENT_CERT', '').value
        self.key = self.declare_parameter('PYTAK_TLS_CLIENT_KEY', '').value
        self.ca = self.declare_parameter('PYTAK_TLS_CLIENT_CAFILE', '').value
        # ADB forwarding can discard pending downstream data on immediate EOF.
        # Only USB direct-to-ATAK connections need this bounded flush allowance.
        self.direct_flush_seconds = self.declare_parameter('DIRECT_TCP_FLUSH_SECONDS', 0.0).value
        if not 0 <= self.direct_flush_seconds <= 1:
            raise ValueError('DIRECT_TCP_FLUSH_SECONDS must be between 0 and 1')
        self.rx = self.create_publisher(String, 'tak_rx', 100)
        self.subscription = self.create_subscription(String, 'tak_tx', self.enqueue, 100)
        self.outgoing = queue.Queue(maxsize=1000)
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self.run_transport, daemon=True)
        self.worker.start()

    def enqueue(self, msg):
        try:
            if ET.fromstring(msg.data).tag != 'event':
                raise ValueError('expected a CoT event')
            self.outgoing.put_nowait(msg.data.encode('utf-8'))
        except (ET.ParseError, ValueError, queue.Full) as exc:
            self.get_logger().warning(f'CoT rejected: {exc}')

    def run_transport(self):
        parsed = urlparse(self.url)
        if parsed.scheme not in ('udp', 'tcp', 'tls', 'tcp+direct') or not parsed.hostname or not parsed.port:
            self.get_logger().error(f'Unsupported COT_URL: {self.url}')
            return
        if parsed.scheme == 'tcp+direct':
            self.run_direct_transport(parsed)
            return
        pending = None
        while not self.stop.is_set():
            try:
                if parsed.scheme == 'udp':
                    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    connection.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
                    connection.connect((parsed.hostname, parsed.port))
                else:
                    connection = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
                    if parsed.scheme == 'tls':
                        context = ssl.create_default_context(cafile=self.ca or None)
                        if self.cert:
                            context.load_cert_chain(self.cert, self.key or None)
                        connection = context.wrap_socket(connection, server_hostname=parsed.hostname)
                with connection:
                    connection.settimeout(0.1)
                    self.get_logger().info(f'CoT transport connected: {self.url}')
                    buffer = b''
                    while not self.stop.is_set():
                        if pending is None:
                            try:
                                pending = self.outgoing.get_nowait()
                            except queue.Empty:
                                pass
                        if pending is not None:
                            connection.sendall(pending)
                            pending = None
                        try:
                            data = connection.recv(65535)
                            if not data:
                                raise ConnectionError('CoT server closed connection')
                            buffer += data
                            while b'</event>' in buffer:
                                end = buffer.index(b'</event>') + len(b'</event>')
                                event, buffer = buffer[:end], buffer[end:]
                                self.rx.publish(String(data=event.decode('utf-8')))
                            if len(buffer) > 4 * 1024 * 1024:
                                raise ValueError('CoT receive buffer exceeded 4 MiB')
                        except socket.timeout:
                            pass
            except (OSError, ValueError, UnicodeError) as exc:
                self.get_logger().warning(f'CoT connection: {exc}; retrying in 2 seconds')
                self.stop.wait(2)

    def run_direct_transport(self, parsed):
        """ATAK peer TCP input frames ONE CoT by EOF, unlike a TAK Server stream."""
        pending = None
        connected = False
        while not self.stop.is_set():
            if pending is None:
                try:
                    pending = self.outgoing.get(timeout=0.1)
                except queue.Empty:
                    continue
            try:
                with socket.create_connection((parsed.hostname, parsed.port), timeout=5) as connection:
                    connection.sendall(pending)
                    self.stop.wait(self.direct_flush_seconds)
                    connection.shutdown(socket.SHUT_WR)
                pending = None
                if not connected:
                    self.get_logger().info(f'Direct CoT delivery active: {self.url}')
                connected = True
            except OSError as exc:
                connected = False
                self.get_logger().warning(f'Direct CoT connection: {exc}; retrying in 2 seconds')
                self.stop.wait(2)

    def destroy_node(self):
        self.stop.set()
        self.worker.join(timeout=6)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RosTakBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
