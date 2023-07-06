import argparse
import asyncio
from typing import Set
import netifaces
import socket
import threading
import time


import zmq
import zmq.asyncio
import logging
from contextlib import closing


import queue

from lib.net import IPAddress, get_lan_ips, ZeroconfManager
from lib.zmq import Publisher, Subscriber, available_messages

logger = logging.getLogger(__name__)


class ZMQManager(ZeroconfManager):
    def __init__(self, name: str, addresses: Set[IPAddress], port: int):
        super().__init__(name, addresses, port)

        self.publish_queue = queue.SimpleQueue()
        self.subscriber_queue = queue.SimpleQueue()

        self.subscriptions = {}
        self.zmq = zmq.Context()

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
            self.subscriptions[name] = sub
            logger.debug(f"Adding ZMQ subscriber for {name}@{address}")

    def remove_service(self, *args):
        name, address = super().remove_service(*args)

        # __del__ will close the socket during GC
        sub = self.subscriptions.pop(name, None)
        if sub:
            logger.debug(f"Removing ZMQ subscriber for {name}@{address}")

    def get_sock_name(self, fd) -> str:
        for name, sock in self.subscriptions.items():
            if fd == sock.sock.fileno():
                return name

    def get_messages(self):
        socks = [s.sock for s in self.subscriptions.values()]
        for fd, msg in available_messages(socks):
            yield self.get_sock_name(fd), msg


def main(name: str, port: int, message: str):
    addresses = get_lan_ips() | get_lan_ips(v6=True)
    name = name or f"officepal-{socket.gethostname()}"

    with closing(ZMQManager(name, addresses, port)) as z:

        def writer():
            while True:
                z.publisher.sock.send_string(message)
                time.sleep(2)

        writer_thread = threading.Thread(target=writer, daemon=True).start()

        while z:
            try:
                for sock, msg in z.get_messages():
                    print(sock, msg)
            except KeyboardInterrupt:
                break


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

    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    main(name=args.name, port=args.port, message=args.message)
