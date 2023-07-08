import argparse
import socket
import threading
import time
import ui.interface as ui
import logging
from contextlib import closing

from lib.util import get_lan_ips
from lib.net import ZMQManager, ZeroInterface, Subscriber, Publisher
from ui.comms import EventMessage, EventType
from ui.friend import Friend

logger = logging.getLogger(__name__)


class Middleware(ZeroInterface):
    def __init__(self):
        self.ui = ui.UI()
        self.tx_queue = self.ui.rx_queue
        self.rx_queue = self.ui.tx_queue

    def start(self, publisher: Publisher):
        self.publisher = publisher
        self._poll_ui_queue = threading.Thread(target=self._poll_ui_queue, daemon=True).start()
        self.ui.run()

    def on_host_discovered(self, subscriber: Subscriber):
        logger.info("on_host_discovered(): %s" % subscriber.normalized_name())
        self.tx_queue.put(
            EventMessage(type=EventType.FRIEND_DISCOVERED, payload=Friend(subscriber.normalized_name()))
        )

    def on_host_lost(self, subscriber: Subscriber):
        logger.info("on_host_lost(): %s " % subscriber.normalized_name())

    def on_new_message(self, subscriber: Subscriber, message: str):
        logger.info("on_new_message(): %s %s" % subscriber.normalized_name(), message)
        #tx_queue.put(
        #    EventMessage(type=EventType.MESSAGE_RECEIVED, payload=response)
        #)

    def _poll_ui_queue(self):
        while True:
            print("wtf")
            msg = self.rx_queue.get()
            if msg.type == EventType.MESSAGE_SENT:
                m = msg.payload
                if not m.is_loopback():
                    print(m)
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
            middleware.start(zmq.publisher)


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
