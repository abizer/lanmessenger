
import datetime
import zmq

import logging

logger = logging.getLogger(__name__)

class ZMQTransport(object):
    def __init__(self, address: str, port: str, **kwargs):
        super().__init__(**kwargs)
        self.address = address
        self.port = port

        self.zctx = zmq.Context.instance()
        self.cxn = f"tcp://{address}:{port}"
        self.socket = self.zctx.socket(zmq.PUB)
        self.socket.bind(self.cxn)

        self.peers = {}

    def __del__(self):
        self.remove_all_peers()
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
    def recv_from_socket(sock: zmq.Socket):
        return sock.recv_string()

    def recv_from_peer(self, address: str, port: int):
        return self.recv_from_socket(self.peers[(address, port)])

    def recv_from_peers(self):
        r, _, _ = zmq.select(list(self.peers.values()), [], [], timeout=0.1)
        logger.debug(f"recv messages from {len(r)} sockets:")
        for sock in r:
            if sock:
                yield self.recv_from_socket(sock)

    def send_to_peers(self, message: str):
        logger.debug("sending message")
        return self.socket.send_string(message)


class Node(ZMQTransport):
    def __init__(self, node_id: int, **kwargs):
        super().__init__(self, **kwargs)
        self.node_id = node_id
        self.shared_state = []

        self.connect()

    def append_state(self, value):
        ts = datetime.utcnow()
        self.shared_state.append((ts, self.node_id, value))
        self.synchronize()

    def reset_state(self):
        self.shared_state = []
        self.synchronize()
