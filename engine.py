#!/usr/bin/env python3

import argparse
from typing import Any, Dict, List, Set, Optional 
import asyncio

import datetime
from collections import namedtuple 

import socket
from zeroconf import ServiceBrowser, Zeroconf
import threading
import time

import zmq 
import zmq.asyncio

import concurrent.futures

import logging 

logger = logging.getLogger(__name__)

from lib import ZeroconfManager

async def main(args: argparse.Namespace):
    manager = ZeroconfManager(args)

    async def post_messages(manager, message):
        while True:
            timed_message = f"{time.ctime()}: {message}"
            await manager.publisher.publish_message(topic="officepal", message=timed_message)
            await asyncio.sleep(5)

    try:
        print("Starting server...")
        runner = asyncio.create_task(manager.run())
        

        print("Starting publisher...")
        publisher = asyncio.create_task(post_messages(manager, args.message))

        print("Receiving messages...")
        async for msg in manager.listener.get_messages():
            print(msg)

    except KeyboardInterrupt:
        print("Stopping server...")
        runner.cancel()
        publisher.cancel()        

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    hostname = socket.gethostname()
    parser = argparse.ArgumentParser(description="officepal lanmessenger")

    parser.add_argument('--name', type=str, default=f"officepal-{hostname}", help="Service name")
    parser.add_argument('--port', type=int, default=31337, help='Listen port')
    parser.add_argument('--message', type=str, default="Hello from officepal", help='Publish message')

    args = parser.parse_args()

    asyncio.run(main(args))