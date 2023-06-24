#!/usr/bin/env python3

from typing import Any, Dict, List, Set, Optional 

import datetime
from collections import namedtuple 

import socket

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


def main():
    ui = get_ui()


    clients = {'cloud': 'api.0x00.sh:12345'}
    clients += find_clients()

    ui.populate_clients(clients)

def get_ui():
    pass

def find_clients(broadcast_domain):
    # scan network
    return []

if __name__ == '__main__':
    main()