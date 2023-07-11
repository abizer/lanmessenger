import argparse
import queue
import socket
import threading
import time
import json
import lib.ui.interface as ui
import logging
from contextlib import closing

from lib.ui.settings import DevSettings, Settings
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
    EventMessage,
    EventType,
    LOOPBACK_IDENTIFIER,
    Status,
    FriendIdentifier,
)
import lib.ui.event as event
from lib.util import EventQueue

logger = logging.getLogger(__name__)


class UIMiddleware:
    def __init__(self, zmq: ZMQManager, settings: Settings):
        # Ownership of settings is now transferred to the UI. Necessarily, all settings
        # related changes are user driven.
        self.ui = ui.UI(settings=settings)
        self.username = settings.username
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
                m: event.ChatMessagePayload = msg.payload
                if not m.is_loopback():
                    self.zmq.send_message(msg)
            elif msg.type == EventType.USERNAME_CHANGED:
                self.username = msg.payload.username
                self.zmq.send_message(msg)

    def _process_ui_event(self, name, type, payload):
        print(type == EventType.USERNAME_CHANGED)
        if type == EventType.MESSAGE_SENT:
            if payload["to"] == self.publisher.normalized_name:
                self.on_new_message(name, payload["content"])
        elif type == EventType.USERNAME_CHANGED:
            self.on_friend_username_changed(id=name, new_username=payload["username"])
        else:
            print(f"Unknown message typeeee {type}")

    def _process_zmq_event_queue(self):
        for event in self.zmq.get_events():
            if event.type == ZMQEventType.SOCKET_ADDED:
                name, metadata = event.payload
                self.on_friend_discovered(name, metadata["username"])
            elif event.type == ZMQEventType.SOCKET_REMOVED:
                name = event.payload
                self.on_friend_lost(name)
            elif event.type == ZMQEventType.MESSAGE_RECEIVED:
                # message is a json dict, from when we serialized
                # the ChatEventMessage we passed in _process_ui_rx_queue
                name, payload = event.payload
                self._process_ui_event(
                    name=name, type=payload["type"], payload=payload["payload"]
                )

    def on_friend_discovered(self, id: FriendIdentifier, username: str):
        logger.info(f"on_friend_discovered(): {id}:{username}")
        self.tx_queue.put(
            EventMessage(
                type=EventType.FRIEND_STATUS_CHANGED,
                payload=event.StatusChangedPayload(id=id, status=Status.ONLINE),
            )
        )
        self.on_friend_username_changed(id=id, new_username=username)

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

    def on_friend_username_changed(self, id, new_username):
        self.tx_queue.put(
            EventMessage(
                type=EventType.USERNAME_CHANGED,
                payload=event.UsernameChangedPayload(
                    id=id,
                    username=new_username,
                ),
            )
        )


def main(dev_name: str, port: int, mock: bool):
    settings = None
    if len(dev_name) > 0:
        settings = DevSettings(username=dev_name)
    else:
        settings = Settings()

    if mock:
        interface = ui.UI(settings)
        interface.run(mock=True)
    else:
        addresses = get_lan_ips() | get_lan_ips(v6=True)

        username = settings.username
        with closing(ZMQManager(settings.uuid, port)) as zmq:
            with closing(
                ZeroconfManager(
                    settings.uuid,
                    {"username": username},
                    addresses,
                    port,
                    zmq.discover_events,
                )
            ):
                ui = UIMiddleware(zmq, settings)
                ui.run()


def parse_args():
    parser = argparse.ArgumentParser(description="officepal lanmessenger")
    parser.add_argument("--dev-name", type=str, default=f"", help="Service name")
    parser.add_argument("--port", type=int, default=31337, help="Listen port")
    parser.add_argument(
        "--mock", action="store_true", default=False, help="Run the mock UI"
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    main(dev_name=args.dev_name, port=args.port, mock=args.mock)
