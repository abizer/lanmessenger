import argparse
import asyncio
import socket
import threading
import time 
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
import zmq
import zmq.asyncio
import logging
from contextlib import closing

import queue

logger = logging.getLogger(__name__)

ZEROCONF_TYPE = "_officepal._tcp.local."

class ZeroconfManager:
    def __init__(self, name: str = "test", port: int = 31337):
        self.hostname = socket.gethostname()
        self.name = name or f'officepal-{self.hostname}'
        self.port = port
        self.zc = Zeroconf()
        self.zmq = zmq.Context()

        self.publish_queue = queue.SimpleQueue()
        self.subscriber_queue = queue.SimpleQueue()
        
        self.service_info = ServiceInfo(
            ZEROCONF_TYPE,
            f"{self.name}.{ZEROCONF_TYPE}",
            addresses=[socket.inet_aton('127.0.0.1')],
            port=port
        )

        self.friends = {}

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
        self.zc.unregister_service(self.service_info)
        self.publisher.sock.close()
        for friend in self.friends.values():
            friend.sock.close()
        self.zmq.term()

    def add_service(self, zeroconf, type, name):
        svc = zeroconf.get_service_info(type, name)
        if svc.name != f"{self.name}.{ZEROCONF_TYPE}":
            logger.debug(f"Friend found: {svc.name}")
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
        

class Publisher:
    def __init__(self, context, port: int, queue: queue.SimpleQueue):
        self.port = port
        self.context = context
        self.sock = self.context.socket(zmq.PUB)
        self.sock.bind(f"tcp://0.0.0.0:{port}")
        self.queue = queue

        self.thread = threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        while True: 
            msg = self.queue.get()
            self.sock.send_string(msg)
    
    def write(self, message):
        self.queue.put(message)

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

        self.read_thread = threading.Thread(target=self.get, daemon=True).start()

    def get(self):
        while True:
            self.queue.put((self.name, self.sock.recv_string()))

def parse_args():
    hostname = socket.gethostname()
    parser = argparse.ArgumentParser(description="officepal lanmessenger")

    parser.add_argument('--name', type=str, default=f"officepal-{hostname}", help="Service name")
    parser.add_argument('--port', type=int, default=31337, help='Listen port')
    parser.add_argument('--message', type=str, default="Hello from officepal", help='Publish message')

    return parser.parse_args()



def main(name: str, port: int, message: str):
    with closing(ZeroconfManager(port=port, name=name)) as z:
        def writer():
            while True:
                z.publisher.write(message) 
                time.sleep(2)       

        publish_thread = threading.Thread(target=writer, daemon=True).start()

        while True:
            user, msg = z.subscriber_queue.get()
            print(f"{msg} from {user}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    main(name=args.name, port=args.port, message=args.message)
