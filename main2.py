import asyncio 
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf
import zmq
import zmq.asyncio

ZEROCONF_TYPE = "_officepal._tcp.local."

zmqc = zmq.asyncio.Context()

class ZeroconfManager:
    def __init__(self):
        self.zc = AsyncZeroconf() 
        
        self.service_info = AsyncServiceInfo(
            ZEROCONF_TYPE,
            f"{self.name}.{ZEROCONF_TYPE}",
        )


class Publisher:
    def __init__(self, context, port: int):
        self.port = port
        self.context = context
        self.sock = self.context.socket(zmq.PUB)
        self.sock.bind(f"tcp://0.0.0.0:{port}")
    
    async def write(self, message):
        await self.sock.send_string(message)

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

if __name__ == '__main__':
    pass


