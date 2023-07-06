import socket
from typing import Callable, List, Optional, Set, Union
import netifaces
from ipaddress import IPv4Address, IPv6Address

import logging

# from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)

ZEROCONF_TYPE = "_officepal._tcp.local."

IPAddress = Union[IPv4Address, IPv6Address]


def get_lan_ips(v6=False) -> Set[IPAddress]:
    ips = set()
    family = netifaces.AF_INET6 if v6 else netifaces.AF_INET
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        if family in addresses:
            for addr in addresses[family]:
                ip = IPv6Address(addr["addr"]) if v6 else IPv4Address(addr["addr"])
                if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                    ips.add(ip)
    return ips


def make_service_info(name: str, addresses: List[str], port: int) -> ServiceInfo:
    service_info = ServiceInfo(
        type_=ZEROCONF_TYPE,
        name=f"{name}.{ZEROCONF_TYPE}",
        port=port,
        addresses=[ip.packed for ip in addresses],
    )
    return service_info


class ZeroconfManager:
    def __init__(self, name: str, addresses: List[str], port: int):
        self.service_info = make_service_info(name, addresses, port)
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
