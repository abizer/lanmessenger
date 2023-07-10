from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Set
from typing import List, Tuple
import logging
import queue
import socket
import socket
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
from time import sleep

from lib.net.util import IPAddress

logger = logging.getLogger(__name__)


ZEROCONF_TYPE = "_officepal._tcp.local."


class ZeroInterface(ABC):
    @abstractmethod
    def add_subscription(self, name: str, address: str):
        ...

    @abstractmethod
    def drop_subscription(self, name: str, address: str):
        ...


class ZeroconfManager:
    def __init__(
        self, name: str, addresses: List[str], port: int, event_queue: queue.Queue
    ):
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

        self.queue = event_queue
        logger.debug("zeroconf up")

    def close(self):
        self.browser.cancel()
        self.zc.unregister_service(self.service_info)
        self.zc.close()
        logger.debug("zeroconf down")

    def make_address(self, svc: ServiceInfo) -> str:
        dst_address = socket.inet_ntoa(svc.addresses[0])
        return f"{dst_address}:{svc.port}"

    def add_service(self, zeroconf, type, name) -> str:
        svc = zeroconf.get_service_info(type, name)
        address = ""
        if svc.name != self.service_info.name:
            logger.debug(f"discovered friend {name} {address}")
            address = self.make_address(svc)
            self.friends[svc.name] = address

            # put information into the queue so downstream
            # libraries can consume it in a thread-safe way
            if self.queue:
                self.queue.put((name, address))

    def remove_service(self, zeroconf, type, name):
        address = self.friends.pop(name)
        if address:
            logger.debug(f"lost friend {name}")
        if self.queue:
            self.queue.put((name, None))

    def update_service(self, *args):
        pass
