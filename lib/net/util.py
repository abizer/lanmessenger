import queue
from typing import Set, Union
import netifaces
import ipaddress
from ipaddress import IPv4Address, IPv6Address

IPAddress = Union[IPv4Address, IPv6Address]


def get_lan_ips(v6=False) -> Set[IPAddress]:
    ips = set()
    family = netifaces.AF_INET6 if v6 else netifaces.AF_INET
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        if family in addresses:
            for addr in addresses[family]:
                try:
                    ip = IPv6Address(addr["addr"]) if v6 else IPv4Address(addr["addr"])
                    if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                        ips.add(ip)
                except ipaddress.AddressValueError:
                    pass
    return ips
