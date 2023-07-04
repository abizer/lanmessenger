import argparse
import asyncio
import netifaces
import socket
import threading
import time
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
import zmq
import zmq.asyncio
import logging
from contextlib import closing
import ipaddress

import queue

logger = logging.getLogger(__name__)

ZEROCONF_TYPE = "_officepal._tcp.local."

class Publisher:
    def __init__(self, context, port: int, queue: queue.SimpleQueue):
        self.port = port
        self.context = context
        self.sock = self.context.socket(zmq.PUB)
        self.sock.bind(f"tcp://0.0.0.0:{port}")
        self.queue = queue

        self.shutdown_event = threading.Event()
        self.thread = threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        while not self.shutdown_event.is_set():
            msg = self.queue.get()
            self.sock.send_string(msg)

    def write(self, message):
        self.queue.put(message)

    def close(self):
        self.shutdown_event.set()
        self.sock.close()


class Subscriber:
    def __init__(self, context, name, ip, port, queue):
        self.context = context
        self.name = name
        self.ip = ip
        self.port = port
        self.queue = queue

        self.sock = self.context.socket(zmq.SUB)
        self.sock.connect(f"tcp://{ip}:{port}")
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")

        self.read_shutdown = threading.Event()
        self.read_thread = threading.Thread(target=self.get, daemon=True).start()

    def get(self):
        while not self.read_shutdown.is_set():
            self.queue.put((self.name, self.sock.recv_string()))

    def close(self):
        try:
            self.read_shutdown.set()
            self.sock.close()
        except Exception as e:
            logger.error(f"error while shutting down subscriber for {self.name}@{self.ip}:{self.port}", exc_info=e)


def get_lan_ips(v6=False):
    ips  = set([])
    family = netifaces.AF_INET6 if v6 else netifaces.AF_INET
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        if family in addresses:
            for addr in addresses[family]:
                ip = ipaddress.IPv6Address(addr['addr']) if v6 else ipaddress.IPv4Address(addr['addr'])
                if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                    ips.add(ip)
    return ips

class ZeroconfManager:
    def __init__(self, name: str, port: int = 31337):
        self.hostname = socket.gethostname()
        self.name = name or f'officepal-{self.hostname}'
        self.port = port

        self.publish_queue = queue.SimpleQueue()
        self.subscriber_queue = queue.SimpleQueue()

        packed_ips = [ ip.packed for ip in (get_lan_ips() | get_lan_ips(v6=True)) ]

        self.service_info = ServiceInfo(
            ZEROCONF_TYPE,
            f"{self.name}.{ZEROCONF_TYPE}",
            addresses=packed_ips,
            port=port
        )

        self.friends = {}

        self.zc = Zeroconf()
        self.zmq = zmq.Context()

        self.publisher = Publisher(
            context=self.zmq,
            port=self.port,
            queue=self.publish_queue
        )
        self.zc.register_service(self.service_info)
        self.browser = ServiceBrowser(
            self.zc,
            ZEROCONF_TYPE,
            listener=self,
        )



    def close(self):
        self.browser.cancel()
        self.zc.unregister_service(self.service_info)
        self.zc.close()

        self.publisher.close()
        for friend in self.friends.values():
            friend.close()
        self.zmq.term()

    def add_service(self, zeroconf, type, name):
        svc = zeroconf.get_service_info(type, name)
        if svc.name != f"{self.name}.{ZEROCONF_TYPE}":
            name = name.removesuffix("." + ZEROCONF_TYPE)
            logger.debug(f"Friend found: {name}@{address}:{svc.port}")
            subscriber = Subscriber(
                self.zmq,
                name=svc.name,
                ip=socket.inet_ntoa(svc.addresses[0]),
                port=svc.port,
                queue=self.subscriber_queue
            )
            self.friends[svc.name] = subscriber


    def remove_service(self, zeroconf, type, name):
        logger.debug(f"Friend lost: {name}")
        self.friends.pop(name)

    def update_service(self, zeroconf, type, name):
        pass

def parse_args():
    hostname = socket.gethostname()
    parser = argparse.ArgumentParser(description="officepal lanmessenger")

    parser.add_argument('--name', type=str, default=f"officepal-{hostname}", help="Service name")
    parser.add_argument('--port', type=int, default=31337, help='Listen port')
    parser.add_argument('--message', type=str, default="Hello from officepal", help='Publish message')

    return parser.parse_args()

def main(name: str, port: int, message: str):
    with closing(ZeroconfManager(port=port, name=name)) as z:
        writer_shutdown = threading.Event()

        def writer():
            while not writer_shutdown.is_set():
                z.publisher.write(message)
                time.sleep(2)

        writer_thread = threading.Thread(target=writer, daemon=True).start()

        try:
            while True:
                user, msg = z.subscriber_queue.get()
                print(f"{msg} from {user}")
        except KeyboardInterrupt:
            writer_shutdown.set()

def parse_args():
    hostname = socket.gethostname()
    parser = argparse.ArgumentParser(description="officepal lanmessenger")

    parser.add_argument('--name', type=str, default=f"officepal-{hostname}", help="Service name")
    parser.add_argument('--port', type=int, default=31337, help='Listen port')
    parser.add_argument('--message', type=str, default="Hello from officepal", help='Publish message')

    return parser.parse_args()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    main(name=args.name, port=args.port, message=args.message)
