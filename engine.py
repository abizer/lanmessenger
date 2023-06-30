#!/usr/bin/env python3

from typing import Any, Dict, List, Set, Optional 

import datetime
from collections import namedtuple 

import socket
from zeroconf import ServiceBrowser, Zeroconf
import threading
import time

from lib import Server, Client

MessageContext = namedtuple("MessageContext", ['source', 'ts', 'data'])

class Content:
    data: Any

    def __init__(self, data: Any):
        self.data = data 

    def serialize(self) -> bytes:
        return self.data.encode('utf-8')

    @classmethod
    def deserialize(cls, data: bytes) -> "Content":
        # deserialize
        return cls(str(data))


class Connection:
    endpoint: str
    socket: socket.socket

    def __init__(self, endpoint: str, listen: bool = True):
        self.endpoint = endpoint
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if listen:
            self.listen()
        else:
            self.connect()

    def connect(self):
        self.socket.connect(self.endpoint.split(":"))

    def listen(self):
        self.socket.bind(('0.0.0.0', 31337))
        self.socket.listen(5)
        

    def disconnect(self):
        pass 

    def send(self, payload: bytes):
        for i in range(0, len(payload), 4096):
            chunk = payload[i:i+4096]
            self.socket.sendall(chunk)

    def receive(self) -> bytes:
        while True:
            c, addr = self.socket.accept()
            #print(f"DEBUG: Got connection from {addr}")
            while True:
                # receive data from client
                received_data = c.recv(4096)
                if not received_data:
                    break
                else:
                    yield received_data
            c.close()


class Client:
    name: str
    cxn: Connection
    endpoint: str = ""
    history: List = []

    def __init__(self, name: str, endpoint: str):
        self.name = name
        self.cxn = Connection(self.endpoint)
        self.history = []

    def send_message(self, message: str) -> bool:
        c = MessageContext(source=self.name, ts=datetime.now(), data=message)
        self.history.append(c)

        ser = Content(message).serialize()
        self.cxn.send(ser)

    def receive_message(self, message: str) -> str:
        data = self.cxn.read()
        c = MessageContext(source=self.name, ts=datetime.now(), data=data)
        message = Content.deserialize(data)
        self.history.append(c)
        return message


class Discover:
    def __init__(self, name: str):
        self.name = name
        self.found_services = {}

    def remove_service(self, zeroconf, type, name):
        c = self.found_services.pop(name)
        c.stop()
        print(f"Service {name} removed")

    def add_service(self, zeroconf, type, name):
        service = zeroconf.get_service_info(type, name)

        if service.name != self.name:
            client = Client(socket.inet_ntoa(service.addresses[0]), service.port)
            print(f"Connecting to {client}")
            client_thread = threading.Thread(target=client.listen_for_messages, daemon=True)
            client_thread.start()

        self.found_services[name] = client_thread
        print(f"{service.name} added")

    def update_service(self, zeroconf, type, name):
        pass

    def __str__(self):
        return str(set(self.found_services))

def main():
    hostname = socket.gethostname()
    chat_server = Server(f"officepal-{hostname}", 5000)
    listener = Discover()
    zeroconf = Zeroconf()

    print(f"Registering {chat_server.info.type}...")
    zeroconf.register_service(chat_server.info)

    def listen():
        browser = ServiceBrowser(zeroconf, "_officepal._tcp.local.", listener)
        time.sleep(1)


    listen_thread = threading.Thread(target=listen)
    listen_thread.start()

    browser = ServiceBrowser(zeroconf, "_officepal._tcp.local.", listener)
    time.sleep(1)  # allow some time for services to be discovered

    client_threads = []

    for service in listener.found_services:
        if service.name != chat_server.info.name:
            chat_client = Client(socket.inet_ntoa(service.addresses[0]), service.port)
            print(f"Connecting to {chat_client}")
            client_thread = threading.Thread(target=chat_client.listen_for_messages, daemon=True)
            client_thread.start()
            client_threads.append(client_thread)

    try:
        while True:
            message = f"Server message at {time.ctime()}"
            chat_server.publish_message(message)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nInterrupt received, stopping server...")
    finally:
        print("Unregistering service...")
        zeroconf.unregister_service(chat_server.info)
        zeroconf.close()
        print("Service unregistered.")

if __name__ == '__main__':
    main()