import queue
import socket
import threading
from types import SimpleNamespace
from urllib.parse import urlparse
from rostak.rostak_bridge import RosTakBridge


def test_direct_tcp_uses_one_complete_event_per_connection():
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen()
    server.settimeout(5)
    url = f'tcp+direct://127.0.0.1:{server.getsockname()[1]}'
    outgoing = queue.Queue()
    messages = [b'<event uid="one"></event>', b'<event uid="two"></event>']
    for message in messages:
        outgoing.put(message)
    node = SimpleNamespace(outgoing=outgoing, stop=threading.Event(), url=url, direct_flush_seconds=0,
                           get_logger=lambda: SimpleNamespace(info=lambda _: None, warning=lambda _: None))
    worker = threading.Thread(target=RosTakBridge.run_direct_transport, args=(node, urlparse(url)))
    worker.start()
    received = []
    try:
        for _ in messages:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(5)
                data = b''
                while True:
                    part = connection.recv(4096)
                    if not part:
                        break
                    data += part
                received.append(data)
        assert received == messages
    finally:
        node.stop.set()
        worker.join(timeout=6)
        server.close()
    assert not worker.is_alive()
