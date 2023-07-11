
import datetime
import zmq

class ZMQTransport(object):
    def __init__(self, address: str, port: str, **kwargs):
        super().__init__(**kwargs)
        self.address = address
        self.port = port

        self.zctx = zmq.Context.instance()
        self.cxn = f"tcp://{address}:{port}"
        self.socket = self.zctx.socket(zmq.PUB, self.cxn)
        self.peers = {}

    def add_peer(self, address: str, port: str):
        cxn = f"tcp://{address}:{port}"
        peer_sock = self.zctx.socket(zmq.SUB, cxn)
        self.peers[cxn] = peer_sock

    def remove_peer(self, address: str, port: str):
        cxn = f"tcp://{address}:{port}"
        sock = self.peers.get(cxn, None)
        if sock:
            sock.close()

    @staticmethod
    def recv_from_socket(sock: zmq.Socket):
        return sock.recv_string()

    def recv_from_peer(self, peer_cxn: str):
        return self.recv_from_socket(self.peers[peer_cxn])

    def recv_from_peers(self):
        r, _, = zmq.select(self.peers, [], [], timeout=0.1)
        for sock in r:
            yield self.recv_from_socket(sock)

    def send_to_peers(self, message: str):
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

    def reset(self):
        self.shared_state = []
        self.synchronize()
