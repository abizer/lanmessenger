import argparse
import queue
import socket
import threading
import time
import json
import lib.ui.interface as ui
import logging
from contextlib import closing

from lib.ui.settings import Settings
from lib.net.util import get_lan_ips
from lib.net.zeroconf import ZeroconfManager
from lib.net.zmq import (
    ZMQEvent,
    ZMQEventType,
    ZMQManager,
    Subscriber,
    Publisher,
)
from lib.ui.event import (
    ChatMessagePayload,
    EventMessage,
    EventType,
    FriendIdentifier,
    LOOPBACK_IDENTIFIER,
    Status,
    StatusChangedPayload,
)
import lib.ui.event as event
from lib.util import EventQueue

logger = logging.getLogger(__name__)


class UIMiddleware:
    def __init__(self, zmq: ZMQManager, settings: Settings):
        # Ownership of settings is now transferred to the UI. Necessarily, all settings
        # related changes are user driven.
        self.ui = ui.UI(settings=settings)
        self.tx_queue = self.ui.rx_queue
        self.rx_queue = self.ui.tx_queue

        self.zmq = zmq
        self.publisher = zmq.publisher
        self.network_events = zmq.subscriber_events

        self._ui_rx_queue_processor = threading.Thread(
            target=self._process_ui_rx_queue, daemon=True
        ).start()
        self._zmq_event_processor = threading.Thread(
            target=self._process_zmq_event_queue, daemon=True
        ).start()

    def run(self):
        self.ui.run()

    def _process_ui_rx_queue(self):
        while True:
            msg: EventMessage = self.rx_queue.get()
            if msg.type == EventType.MESSAGE_SENT:
                m: ChatMessagePayload = msg.payload
                if not m.is_loopback():
                    self.zmq.send_message(msg)
            else:
                logging.info(f"Unknown message type: {msg.type}")

    def _process_ui_event(self, name, event):
        if event["type"] == EventType.MESSAGE_SENT:
            payload = event["payload"]
            if payload['to'] == self.publisher.normalized_name:
                self.on_new_message(name, payload["content"])

    def _process_zmq_event_queue(self):
        for event in self.zmq.get_events():
            if event.type == ZMQEventType.SOCKET_ADDED:
                name = event.payload
                self.on_friend_discovered(name)
            elif event.type == ZMQEventType.SOCKET_REMOVED:
                name = event.payload
                self.on_friend_lost(name)
            elif event.type == ZMQEventType.MESSAGE_RECEIVED:
                # message is a json dict, from when we serialized
                # the ChatEventMessage we passed in _process_ui_rx_queue
                name, payload = event.payload
                self._process_ui_event(name=name, event=payload)

    def on_friend_discovered(self, name: str):
        logger.info(f"on_friend_discovered(): {name}")
        self.tx_queue.put(
            EventMessage(
                type=EventType.FRIEND_STATUS_CHANGED,
                payload=event.StatusChangedPayload(id=name, status=Status.ONLINE),
            )
        )

    def on_friend_lost(self, name: str):
        logger.info(f"on_friend_lost(): {name}")
        self.tx_queue.put(
            EventMessage(
                type=EventType.FRIEND_STATUS_CHANGED,
                payload=event.StatusChangedPayload(id=name, status=Status.OFFLINE),
            )
        )

    def on_new_message(self, name, message: str):
        logger.info(f"on_new_message(): {name, message}")
        self.tx_queue.put(
            EventMessage(
                type=EventType.MESSAGE_RECEIVED,
                payload=event.ChatMessagePayload(
                    content=message,
                    author=name,
                    to=LOOPBACK_IDENTIFIER,
                ),
            )
        )


def main(name: str, port: int, message: str, mock):
    settings = Settings(username=name)
    if mock:
        interface = ui.UI(settings)
        interface.run(mock=True)
    else:
        addresses = get_lan_ips() | get_lan_ips(v6=True)
        name = settings.username

        with closing(ZMQManager(name, port)) as zmq:
            with closing(ZeroconfManager(name, addresses, port, zmq.discover_events)):
                ui = UIMiddleware(zmq, settings)
                ui.run()


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
