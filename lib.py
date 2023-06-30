import zmq
from zeroconf import ServiceInfo, Zeroconf
import socket
import threading

import logging 

logger = logging.getLogger(__name__)

class Server:
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = port
        self.context = zmq.Context()

        self.local_ip = socket.gethostbyname(socket.gethostname())

        # create a PUB socket
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://{self.local_ip}:{self.port}")

        # create a Zeroconf service info object
        self.info = ServiceInfo(
            "_officepal._tcp.local.",
            f"{self.service_name}._officepal._tcp.local.",
            addresses=[socket.inet_aton(self.local_ip)],
            port=self.port,
        )

    def publish_message(self, message: str):
        logger.debug(f"{self.service_name} publishing message: {message}")
        self.publisher.send_string(message)

class Client:
    def __init__(self, server_ip: str, port: int):
        self.server_ip = server_ip
        self.port = port
        self.context = zmq.Context()
        self.channels = {}

        # set 'officepal' as the default topic
        default_channel = self.context.socket(zmq.SUB)
        default_channel.connect(f"tcp://{self.server_ip}:{self.port}")
        default_channel.setsockopt_string(zmq.SUBSCRIBE, "officepal")
        self.channels['default'] = default_channel

    def __str__(self):
        return f"officepal@{self.server_ip}{self.port}"

    def listen_for_messages(self):
        while True:
            topic, message = self.subscriber.recv_string().split(" ", 1)
            yield topic, message

