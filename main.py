import argparse
import socket
import threading
import time
import ui.interface as ui
import logging
from contextlib import closing

from lib.util import get_lan_ips
from lib.net import ZMQManager, ZeroInterface, Subscriber

logger = logging.getLogger(__name__)


class EventMessage:
    def __init__(self, type, payload):
        self.type = type
        self.payload = payload


class Middleware(ZeroInterface):
    def __init__(self):
        self.ui = ui.UI()
        self.tx_queue = self.ui.rx_queue
        self.rx_queue = self.ui.tx_queue

    def start(self, zmq, message):
        def _network_events_thread():
            while zmq:
                try:
                    for sock, msg in zmq.get_messages():
                        print(sock, msg)
                except KeyboardInterrupt:
                    break

        def _ui_events_thread():
            while True:
                zmq.publisher.sock.send_string(message)
                time.sleep(2)

        threading.Thread(target=_network_events_thread, daemon=True).start()
        threading.Thread(target=_ui_events_thread, daemon=True).start()
        self.ui.run()

    def on_host_discovered(self, subscriber: Subscriber):
        logger.info("on_host_discovered(): %s" % subscriber.name)

    def on_host_lost(self, subscriber: Subscriber):
        logger.info("on_host_lost(): %s " % subscriber.name)

    def on_new_message(self, subscriber: Subscriber, message: str):
        pass


def main(name: str, port: int, message: str, mock):
    if mock:
        interface = ui.UI()
        interface.run(mock=True)
    else:
        addresses = get_lan_ips() | get_lan_ips(v6=True)
        name = name or f"officepal-{socket.gethostname()}"

        middleware = Middleware()
        with closing(ZMQManager(middleware, name, addresses, port)) as zmq:
            middleware.start(zmq, message)


def parse_args():
    hostname = socket.gethostname()
    parser = argparse.ArgumentParser(description="officepal lanmessenger")

    parser.add_argument(
        "--name", type=str, default=f"officepal-{hostname}", help="Service name"
    )
    parser.add_argument("--port", type=int, default=31337, help="Listen port")
    parser.add_argument(
        "--message", type=str, default="Hello from officepal", help="Publish message"
    )
    parser.add_argument(
        "--mock", action="store_true", default=False, help="Run the mock UI"
    )

    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    main(name=args.name, port=args.port, message=args.message, mock=args.mock)
