import argparse
import asyncio
import socket
import threading 
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
import zmq
import zmq.asyncio
import logging

import queue

from ui import UI

logger = logging.getLogger(__name__)

ZEROCONF_TYPE = "_officepal._tcp.local."

class ZeroconfManager:
    def __init__(self):
        self.zc = AsyncZeroconf() 
        
        self.service_info = AsyncServiceInfo(
            ZEROCONF_TYPE,
            f"{self.name}.{ZEROCONF_TYPE}",
            addresses=[socket.gethostbyname('0.0.0.0')]
        )


class Publisher:
    def __init__(self, context, port: int, queue: queue.SimpleQueue):
        self.port = port
        self.context = context
        self.sock = self.context.socket(zmq.PUB)
        self.sock.bind(f"tcp://0.0.0.0:{port}")
        self.queue = queue

        self.thread = threading.Thread(target=self.worker, daemon=True).start()

    async def worker(self):
        while True: 
            msg = self.queue.get()
            await self.sock.send_string(msg)
    
    async def write(self, message):
        await self.queue.put

    

class Subscriber:
    def __init__(self, context, ip, port):
        self.context = context 
        self.ip = ip
        self.port = port

        self.sock = self.context.socket(zmq.SUB)
        self.sock.connect(f"tcp://{ip}:{port}")
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")

    async def get(self):
        while True:
            msg = await self.sock.recv_string()
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


