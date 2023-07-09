from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Set
from typing import List, Tuple
import logging
import queue
import socket
import socket
import threading
import zmq

from lib.net.util import IPAddress
from lib.util import EventQueue

logger = logging.getLogger(__name__)


class ZMQEventType(Enum):
    SOCKET_ADDED = 1
    SOCKET_REMOVED = 2
    MESSAGE_RECEIVED = 3


@dataclass
class ZMQEvent:
    type: ZMQEventType
    payload: Any


class Socket:
    ctx: zmq.Context
    sock: zmq.Socket
    name: str

    def __init__(
        self, socktype: zmq.SocketType, name: str, cxn: str, ctx: zmq.Context = None
    ):
        self.ctx = ctx or zmq.Context.instance()
        self.socktype = socktype
        self.name = name
        self.cxn = cxn

        self.sock = self.ctx.socket(self.socktype)

    @property
    def normalized_name(self):
        return self.name.split(".")[0]

    def __str__(self):
        return f"{self.normalized_name}.{self.cxn}"

    def close(self):
        self.sock.close()

    def is_closed(self):
        return self.sock.closed

    def __del__(self):
        self.close()


class Publisher(Socket):
    def __init__(self, name: str, cxn: str):
        super().__init__(zmq.PUB, name, cxn)

        self.sock.bind(self.cxn)
        logger.debug(f"Publisher socket {name}@{cxn} up")

    def send_message(self, message: str):
        self.sock.send_string(message)


class Subscriber(Socket):
    def __init__(self, name: str, cxn: str):
        super().__init__(zmq.SUB, name, cxn)

        self.sock.connect(self.cxn)
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.debug(f"Subscriber socket {name}@{cxn} up")


def available_messages(sockets: List["Subscriber"]) -> Tuple[str, str]:
    try:
        r, _, _ = zmq.select(sockets, [], [], timeout=0.1)
        return [(sock.fileno(), sock.recv_string()) for sock in r if sock]
    except zmq.error.ZMQError as e:
        logger.error(f"error while reading from zmq socket: {e}")
        return []


class ZMQManager:
    def __init__(self, name: str, port: int):
        # we populate this for external use
        self.subscriber_events = EventQueue()

        # this gets populated externally
        self.discover_events = EventQueue()

        self.subscriptions = {}
        self.zmq = zmq.Context.instance()

        # for now, bind to 0.0.0.0
        cxn = f"tcp://0.0.0.0:{port}"
        self.publisher = Publisher(name=name, cxn=cxn)
        self.message_poller_thread = threading.Thread(
            target=self._poll_for_events, daemon=True
        ).start()

        logger.debug(f"zmq up")

    def close(self):
        logger.debug("shutting down zmq sockets")
        self.publisher.close()
        for sub in self.subscriptions.values():
            sub.close()
        self.zmq.term()

    @staticmethod
    def fmt_address(address):
        return f"tcp://{address}"

    @staticmethod
    def _normalize_name(name: str):
        return name.split(".")[0]

    def on_add_subscription(self, name: str, address: str):
        """Instantiate a socket when we get a new address
        from the events queue.
        """
        sub = Subscriber(name=self._normalize_name(name), cxn=self.fmt_address(address))
        self.subscriptions[sub.name] = sub
        logger.debug(f"Added ZMQ subscriber for {sub}")
        return sub

    def on_drop_subscription(self, name: str):
        sub = self.subscriptions.pop(self._normalize_name(name), None)
        if sub:
            logger.debug(f"Removing ZMQ subscriber for {sub}")
            return sub

    def _poll_for_events(self):
        def _sub_from_fd(fd) -> str:
            for sub in self.subscriptions.values():
                if fd == sub.sock.fileno():
                    return sub

        while True:
            # first process any new sockets we need to create
            # or remove, so we avoid thread safety issues in select
            while self.discover_events.size() > 0:
                name, address = self.discover_events.get()
                if address:
                    sub = self.on_add_subscription(name, address)
                    self.subscriber_events.put(
                        ZMQEvent(ZMQEventType.SOCKET_ADDED, sub.name)
                    )
                else:
                    sub = self.on_drop_subscription(name)
                    self.subscriber_events.put(
                        ZMQEvent(ZMQEventType.SOCKET_REMOVED, sub.name)
                    )

            socks = [s.sock for s in self.subscriptions.values()]
            for fd, message in available_messages(socks):
                name = _sub_from_fd(fd).name
                self.subscriber_events.put(
                    ZMQEvent(ZMQEventType.MESSAGE_RECEIVED, (name, message))
                )
                logger.debug(f"Received message from {name}: {message}")
