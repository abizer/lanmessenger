import argparse
import asyncio
import socket
import threading 
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
import zmq
import zmq.asyncio
import logging

import queue

from ui import UI

logger = logging.getLogger(__name__)

ZEROCONF_TYPE = "_officepal._tcp.local."

class ZeroconfManager:
    def __init__(self, port: int = 31337, name=""):
        self.hostname = socket.gethostname()
        self.name = name or f'officepal-{self.hostname}'
        self.port = port
        self.zc = Zeroconf()
        self.zmq = zmq.Context()

        self.publish_queue = queue.SimpleQueue()

        self.publisher = Publisher(context=self.zmq, port=self.port, queue=self.publish_queue)
        
        self.service_info = ServiceInfo(
            ZEROCONF_TYPE,
            f"{self.name}.{ZEROCONF_TYPE}",
            addresses=[socket.inet_aton('127.0.0.1')],
            port=port
        )

        self.zc.register_service(self.service_info)
        self.friends = {}

        self.browser = ServiceBrowser(
            self.zc, 
            ZEROCONF_TYPE, 
            listener=self,
        )

    def __del__(self):
        self.zc.unregister_service(self.service_info)
        self.zmq.term()

    def add_service(self, zeroconf, type, name):
        svc = zeroconf.get_service_info(type, name)
        if svc.name != f"{self.name}.{ZEROCONF_TYPE}":
            logger.debug(f"Friend found: {svc.name}")
            subscriber = Subscriber(self.zmq, ip=socket.inet_ntoa(svc.addresses[0]), port=svc.port)
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
    def __init__(self, context, ip, port):
        self.context = context 
        self.ip = ip
        self.port = port

        self.sock = self.context.socket(zmq.SUB)
        self.sock.connect(f"tcp://{ip}:{port}")
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")

    def get(self):
        while True:
            msg = self.sock.recv_string()
            yield msg

def parse_args():
    hostname = socket.gethostname()
    parser = argparse.ArgumentParser(description="officepal lanmessenger")

    parser.add_argument('--name', type=str, default=f"officepal-{hostname}", help="Service name")
    parser.add_argument('--port', type=int, default=31337, help='Listen port')
    parser.add_argument('--message', type=str, default="Hello from officepal", help='Publish message')

    args = parser.parse_args()

    asyncio.run(main(args))

async def main(args: argparse.Namespace):
    pubq = queue.SimpleQueue()
    subq = queue.SimpleQueue()

    zmqc = zmq.asyncio.Context()

    publisher = Publisher(zmqc, args.port)

    run_context = {
        'pubq': pubq,
        'subq': subq,
    }

    ui = UI(run_context)
    ui.run()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    #args = parse_args()
    #asyncio.run(main(args))


