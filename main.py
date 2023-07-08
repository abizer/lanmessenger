import argparse
import socket
import threading
import time
import lib.ui.interface as ui
import logging
from contextlib import closing

from lib.net.util import get_lan_ips
from lib.net.zero import ZMQManager, ZeroInterface, Subscriber, Publisher
from lib.ui.event import (
    EventMessage,
    EventType,
    FriendIdentifier,
    LOOPBACK_IDENTIFIER,
    Status,
)
import lib.ui.event as event

logger = logging.getLogger(__name__)


class Middleware(ZeroInterface):
    def __init__(self):
        self.ui = ui.UI()
        self.tx_queue = self.ui.rx_queue
        self.rx_queue = self.ui.tx_queue

    def start(self, publisher: Publisher):
        self._ui_queue_processor = threading.Thread(
            target=self._process_ui_queue, args=(publisher,), daemon=True
        ).start()
        self.ui.run()

    def on_host_discovered(self, subscriber: Subscriber):
        logger.info("on_host_discovered(): %s" % subscriber.normalized_name())
        self.tx_queue.put(
            EventMessage(
                type=EventType.FRIEND_STATUS_CHANGED,
                payload=event.StatusChangedPayload(
                    id=subscriber.normalized_name(), status=Status.ONLINE
                ),
            )
        )

    def on_host_lost(self, subscriber: Subscriber):
        logger.info("on_host_lost(): %s " % subscriber.normalized_name())
        self.tx_queue.put(
            EventMessage(
                type=EventType.FRIEND_STATUS_CHANGED,
                payload=event.StatusChangedPayload(
                    id=subscriber.normalized_name(), status=Status.OFFLINE
                ),
            )
        )

    def on_new_message(self, subscriber: Subscriber, message: str):
        logger.info(f"on_new_message(): {subscriber.normalized_name(), message}")
        self.tx_queue.put(
            EventMessage(
                type=EventType.MESSAGE_RECEIVED,
                payload=event.ChatMessagePayload(
                    content=message,
                    author=subscriber.normalized_name(),
                    to=LOOPBACK_IDENTIFIER,
                ),
            )
        )

    def _process_ui_queue(self, publisher):
        while True:
            msg = self.rx_queue.get()
            if msg.type == EventType.MESSAGE_SENT:
                m = msg.payload
                if not m.is_loopback():
                    publisher.send_message(m.content)


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
