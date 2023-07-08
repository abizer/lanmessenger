from abc import ABC, abstractmethod
from typing import List, Set
from typing import List, Tuple
import logging
import queue
import socket
import socket
import threading
import zmq
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf

from lib.util import IPAddress

logger = logging.getLogger(__name__)

ZEROCONF_TYPE = "_officepal._tcp.local."


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


class ZeroInterface(ABC):
    @abstractmethod
    def on_host_discovered(self, subscriber: Subscriber):
        ...

    @abstractmethod
    def on_host_lost(self, subscriber: Subscriber):
        ...

    @abstractmethod
    def on_new_message(self, subscriber: Subscriber, message: str):
        ...


class ZeroconfManager:
    def __init__(self, ziface: ZeroInterface, name: str, addresses: List[str], port: int):
        self.ziface = ziface
        self.service_info = ServiceInfo(
            type_=ZEROCONF_TYPE,
            name=f"{name}.{ZEROCONF_TYPE}",
            port=port,
            addresses=[ip.packed for ip in addresses],
        )
        self.friends = {}

        self.zc = Zeroconf()
        self.zc.register_service(self.service_info)
        self.browser = ServiceBrowser(
            self.zc,
            ZEROCONF_TYPE,
            listener=self,
        )

    def close(self):
        logger.debug("shutting down zeroconf")
        self.browser.cancel()
        self.zc.unregister_service(self.service_info)
        self.zc.close()

    def make_address(self, svc: ServiceInfo) -> str:
        dst_address = socket.inet_ntoa(svc.addresses[0])
        return f"{dst_address}:{svc.port}"

    def add_service(self, zeroconf, type, name) -> str:
        svc = zeroconf.get_service_info(type, name)
        address = ""
        if svc.name != self.service_info.name:
            address = self.make_address(svc)
            self.friends[svc.name] = address
            logger.debug(f"Friend found: {name}@{address}")

        return name, address

    def remove_service(self, zeroconf, type, name):
        address = self.friends.pop(name)
        logger.debug(f"Friend lost: {name}@{address}")
        return name, address

    def update_service(self, zeroconf, type, name):
        pass


class ZMQManager(ZeroconfManager):
    def __init__(
        self, ziface: ZeroInterface, name: str, addresses: Set[IPAddress], port: int
    ):
        super().__init__(ziface, name, addresses, port)

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
            logger.debug(f"Adding ZMQ subscriber for {name}@{address}")
            sub = Subscriber(ctx=self.zmq, name=name, cxn=address)
            with self.mutex:
                self.subscriptions[name] = sub
            self.ziface.on_host_discovered(sub)

    def remove_service(self, *args):
        name, address = super().remove_service(*args)
        self.ziface.on_host_lost(sub)

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
