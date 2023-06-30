import argparse
import asyncio
from typing import Optional
import zmq
import zmq.asyncio
from zeroconf import ServiceInfo, Zeroconf, ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
import socket
import threading

import logging

logger = logging.getLogger(__name__)

ZEROCONF_TYPE = "_officepal._tcp.local."


class ZeroconfManager:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.name = args.name
        self.port = args.port

        self.zc = AsyncZeroconf()
        self.zmq = zmq.asyncio.Context()

        self.browser: Optional[AsyncServiceBrowser] = None
        self.listener = ZeroconfListener(context=self.zmq, name=self.name)
        
        # zmq server we use for publishing messages
        self.publisher = ChatServer(self.zmq, self.name, self.port)
        self.service_info = AsyncServiceInfo(
            ZEROCONF_TYPE,
            f"{self.name}.{ZEROCONF_TYPE}",
            addresses=[self.publisher.address],
            port=self.publisher.port,
        )

        # zmq servers we are subscribed to
        self.subscriptions = []

    async def register_self(self):
        logger.debug("registering service")
        await self.zc.async_register_service(self.service_info)

    async def unregister_self(self):
        logger.debug("unregistering service")
        await self.zc.async_unregister_service(self.service_info)

    async def run(self) -> None:
        try:
            await self.register_self()
            logger.info(f"Discovering services of type {ZEROCONF_TYPE}")
            self.browser = AsyncServiceBrowser(
                self.zc.zeroconf, ZEROCONF_TYPE, listener=self.listener
            )

            # leave it running
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError as e:
            logger.debug(e, exc_info=e)
            await self.unregister_self()
            raise
        finally:
            await self.zc.async_close()
            self.zmq.term()


class ZeroconfListener:
    def __init__(self, context, name: str):
        self.name = name
        self.zmq_context = context
        self.found_services = {}
        self.tasks = []

    def remove_service(self, zeroconf, type, name):
        c = self.found_services.pop(name)
        c.join()
        print(f"Service {name} removed")

    def add_service(self, zeroconf, type, name):
        service = zeroconf.get_service_info(type, name)

        if service.name != self.name:
            client = ChatClient(
                context=self.zmq_context,
                server_ip=socket.inet_ntoa(service.addresses[0]),
                port=service.port,
            )
            print(f"Connecting to {client}")
            self.found_services[name] = client
            self.tasks.append(client.get)
            print(f"{service.name} added")

    def update_service(self, zeroconf, type, name):
        pass

    def __str__(self):
        return str(set(self.found_services))

    async def get_messages(self):
        for message in asyncio.as_completed(self.tasks):
            yield await message


class ChatServer:
    def __init__(self, context, service_name: str, port: int):
        self.service_name = service_name
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.address = socket.inet_aton(self.local_ip)
        self.port = port
        self.context = context

        # create a PUB socket
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://{self.local_ip}:{self.port}")

    async def publish_message(self, topic: str, message: str):
        logger.debug(f"{self.service_name} publishing message: {message}")
        await self.publisher.send_string(f"{topic} {message}")


class ChatClient:
    def __init__(self, context, server_ip: str, port: int):
        self.server_ip = server_ip
        self.port = port
        self.context = context
        self.channels = {}

        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(f"tcp://{self.server_ip}:{self.port}")
        # set 'officepal' as the default topic
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "officepal")

    def __str__(self):
        return f"officepal@{self.server_ip}{self.port}"

    async def get(self):
        while True:
            topic, message = await self.subscriber.recv_string().split(" ", 1)
            data = (self.server_ip, self.port, topic, message)
            print(data)
            yield data

    def join(self):
        self.subscriber.close()
