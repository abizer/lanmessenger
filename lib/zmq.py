import queue
import socket
import threading
import logging
from typing import List, Tuple

import zmq

logger = logging.getLogger(__name__)


def available_messages(sockets: List["Subscriber"]) -> Tuple[str, str]:
    try:
        r, _, _ = zmq.select(sockets, [], [], timeout=0.1)
        return [(sock.fileno(), sock.recv_string()) for sock in r if sock]
    except zmq.error.ZMQError as e:
        logger.error(f"error while reading from zmq socket: {e}")
        return []


class ZMQ:
    ctx: zmq.Context
    sock: zmq.Socket
    name: str

    def __init__(self, ctx: zmq.Context, socktype: zmq.SocketType, name: str, cxn: str):
        self.ctx = ctx
        self.socktype = socktype
        self.name = name
        self.cxn = cxn

        self.sock = self.ctx.socket(self.socktype)

    def close(self):
        self.sock.close()

    def is_closed(self):
        return self.sock.closed

    def __del__(self):
        self.close()


class Publisher(ZMQ):
    def __init__(self, ctx: zmq.Context, name: str, cxn: str):
        super().__init__(ctx, zmq.PUB, name, cxn)

        self.sock.bind(self.cxn)


class Subscriber(ZMQ):
    def __init__(self, ctx: zmq.Context, name: str, cxn: str):
        super().__init__(ctx, zmq.SUB, name, cxn)

        self.sock.connect(self.cxn)
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")
