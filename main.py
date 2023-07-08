import argparse
import asyncio
from typing import Set
import netifaces
import socket
import threading
import time
import queue
import ui.interface as ui

import zmq
import zmq.asyncio
import logging
from contextlib import closing
from enum import Enum


import queue

from lib.net import IPAddress, get_lan_ips, ZeroconfManager
from lib.zmq import Publisher, Subscriber, available_messages

logger = logging.getLogger(__name__)

class EventMessage:
    def __init__(self, type, payload):
        self.type = type
        self.payload = payload

class ZMQManager(ZeroconfManager):
    def __init__(self, name: str, addresses: Set[IPAddress], port: int):
        super().__init__(name, addresses, port)

        self.publish_queue = queue.SimpleQueue()
        self.subscriber_queue = queue.SimpleQueue()
        self.network_events = queue.Queue()

        self.subscriptions = {}
        self.zmq = zmq.Context()
        self.mutex = threading.Lock()

        # for now, bind to 0.0.0.0
        cxn = f"tcp://0.0.0.0:{port}"
        self.publisher = Publisher(ctx=self.zmq, name=name, cxn=cxn)

    def close(self):
        logger.debug("shutting down zmq sockets")
        self.publisher.close()
        for sub in self.subscriptions.values():
            sub.close()
        self.zmq.term()

        super().close()

    def make_address(self, *args):
        return f"tcp://{super().make_address(*args)}"

    def add_service(self, *args):
        # returns the connection string for the pal we just discovered
        name, address = super().add_service(*args)
        if address:
            sub = Subscriber(ctx=self.zmq, name=name, cxn=address)
            with self.mutex:
                self.subscriptions[name] = sub
            logger.debug(f"Adding ZMQ subscriber for {name}@{address}")

    def remove_service(self, *args):
        name, address = super().remove_service(*args)

        with self.mutex:
            # __del__ will close the socket during GC
            sub = self.subscriptions.pop(name, None)
            if sub:
                logger.debug(f"Removing ZMQ subscriber for {name}@{address}")

    def get_sock_name(self, fd) -> str:
        for name, sock in self.subscriptions.items():
            if fd == sock.sock.fileno():
                return name

    def get_messages(self):
        with self.mutex:
            socks = [s.sock for s in self.subscriptions.values()]
            for fd, msg in available_messages(socks):
                yield self.get_sock_name(fd), msg


class Middleware:
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


def main(name: str, port: int, message: str, mock):
    if mock:
        interface = ui.UI()
        interface.run(True)
    else:
        addresses = get_lan_ips() | get_lan_ips(v6=True)
        name = name or f"officepal-{socket.gethostname()}"

        with closing(ZMQManager(name, addresses, port)) as zmq:
            middleware = Middleware()
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
    parser.add_argument("--mock", action='store_true', default=False, help="Run the mock UI")

    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    main(name=args.name, port=args.port, message=args.message, mock=args.mock)
