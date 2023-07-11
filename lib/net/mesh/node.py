
import base64
from collections import namedtuple
from dataclasses import dataclass, field
import dataclasses
import datetime
from enum import Enum
import pickle
import queue
import threading
from typing import Any
import zmq

import logging

logger = logging.getLogger(__name__)

class StateEvent(Enum):
    NOOP: False
    VERIFY: True

@dataclass
class StateChange:
    ts: int = field(default_factory=int(datetime.datetime.timestamp()))
    seqno: int
    event: StateEvent
    state: Any


class InMemSharedState:
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.state = {}
        self.next_seqno = 0
        self.state_lock = threading.Lock()

        self.recover_state()

    def recover_state(self):
        pass

    def iter_state_change(self, change: StateChange):
        change = change or StateChange(seqno=self.next_seqno, event=StateEvent.NOOP)
        while change:
            change = yield self.apply_state_change(change)

    def _noop_change(self, change) -> StateChange:
        return dataclasses.replace(change, event=StateEvent.NOOP)

    def _empty_verify(self, change) -> StateChange:
        return dataclasses.replace(change, state=None)

    def apply_state_change(self, change: StateChange) -> StateChange:
        if change.event == StateEvent.NOOP:
            return change

        # change.event == StateEvent.VERIFY
        if not change.state:
            # we got an empty verify. if we don't know about it,
            # we'll learn about it eventually, so return noop
            return self._noop_change(change)

        existing_state = self.state.get(change.seqno, None)
        if existing_state:
            # we got a full verify for a seqno we know about.
            # smaller ts or longest state wins, return the full verify if we won
            if existing_state == min(existing_state, change, key=lambda x: (x.ts, -len(x.state))):
                return existing_state
            else:
                # the change won. return an empty verify
                self.state[change.seqno] = change
                return self._empty_verify(change)
        elif change.seqno >= self.next_seqno:
            # we got a full verify for a seqno we don't know about
            # if the seqno is valid, accept it and return an empty verify
            self.next_seqno = change.seqno + 1
            self.state[change.seqno] = change
            return self._empty_verify(change)
        else:
            # we got a full verify for an invalid seqno we don't know about.
            # any client that sends us one of these is out of sync. return noop
            return self._noop_change(change)



class ZMQTransport(object):
    def __init__(self, address: str, port: str):
        super().__init__()
        self.address = address
        self.port = port

        self.zctx = zmq.Context.instance()
        self.cxn = f"tcp://{address}:{port}"
        self.socket = self.zctx.socket(zmq.PUB)
        self.socket.bind(self.cxn)

        self.peers = {}

    def __del__(self):
        self.remove_all_peers()
        logger.debug(f"closing pub socket on {self.cxn}")
        self.socket.close()

    def add_peer(self, address: str, port: str):
        peer_sock = self.zctx.socket(zmq.SUB)
        peer_sock.connect(f"tcp://{address}:{port}")
        peer_sock.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.debug(f"connected to {address}:{port}")
        self.peers[(address, port)] = peer_sock

    def remove_peer(self, address: str, port: str):
        sock = self.peers.pop((address, port), None)
        if sock:
            logger.debug(f"disconnect from {address}:{port}")
            sock.close()

    def remove_all_peers(self):
        for peer in list(self.peers.keys()):
            self.remove_peer(*peer)

    @staticmethod
    def recv_from_socket(sock: zmq.Socket) -> Any:
        return ZMQTransport.deserialize(sock.recv())

    def recv_from_peer(self, address: str, port: int):
        return self.recv_from_socket(self.peers[(address, port)])

    def recv_from_peers(self):
        r, _, _ = zmq.select(list(self.peers.values()), [], [], timeout=0.1)
        logger.debug(f"recv messages from {len(r)} sockets:")
        for sock in r:
            if sock:
                yield self.recv_from_socket(sock)

    @staticmethod
    def serialize(content: Any):
        return pickle.dumps(content)

    @staticmethod
    def deserialize(content: bytes) -> Any:
        return pickle.loads(content)

    def send_to_peers(self, content: Any):
        logger.debug("sending message")
        return self.socket.send(self.serialize(content))


class Node(ZMQTransport):
    def __init__(self, node_id: int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_id = node_id


    def load_state(self, state_fn: str):
        with open(state_fn, 'r') as f:
            for serialized in f.readlines():
                change = pickle.loads(base64.decodebytes(serialized))
                self.shared_state.append(change)

    def save_state(self, state_fn: str):
        with open(state_fn, "w") as f:
            for change in self.shared_state:
                f.write(base64.encodebytes(pickle.dumps(change)) + b"\n")


    def append_state(self, value):
        ts = datetime.datetime.utcnow()
        content = (self.seqno, ts, self.node_id, value)
        with self.state_lock:
            self.shared_state.append(content)
            self.seqno += 1
        self.synchronize(content)

    def reset_state(self):
        with self.state_lock:
            self.shared_state = []
            self.seqno = 0
        self.synchronize([])

    def synchronize(self, content=None):
        # first, publish our state
        if content:
            self.send_to_peers(content)
        # then, get any updates from others.
        # we maintain order on ts as an invariant
        changes = self.recv_from_peers()
        with self.state_lock:
            # start reading the generator inside the lock
            # so we hold it for the least amount of time
            for change in changes:
                logger.debug(f"synchronizing change: {change}")
                self.shared_state.append(change)
            # sort to maintain invariant
            self.shared_state.sort(key=lambda x: x[0])
