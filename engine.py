#!/usr/bin/env python3

from typing import Any, Dict, List, Set, Optional 

import datatime
from collections import namedtuple 

MessageContext = namedtuple("MessageContext", ['source', 'ts', 'data'])

class Content:
    data: Any

    def __init__(self, data: Any):
        self.data = data 

    def serialize(self) -> bytes:
        pass 

    @classmethod
    def deserialize(cls, data: bytes) -> "Content":
        # deserialize
        return cls(data)


class Connection:
    endpoint: str
    socket: Dict

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.socket = {}

    def connect(self):
        pass 

    def disconnect(self):
        pass 

    def send(self, payload: bytes):
        self.socket.write(payload)

    def receive(self) -> bytes:
        message = self.socket.read()
        return message


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
        c = MessageContext(source=self.name, ts=datatime.now(), data=data)
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