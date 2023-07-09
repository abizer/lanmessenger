from enum import Enum
import queue


class EventType(Enum):
    ###########################################
    # New friend discovered in the LAN
    FRIEND_DISCOVERED = (1,)
    # Friend is either online, away, offline
    FRIEND_STATUS_CHANGED = (2,)
    # Message came in over the network
    MESSAGE_RECEIVED = (3,)

    ###########################################
    # Send message over the network
    MESSAGE_SENT = (4,)


class EventMessage:
    def __init__(self, type, payload):
        self.type = type
        self.payload = payload


class EventQueue:
    def __init__(self):
        self.fifo = queue.Queue()

    def get(self):
        return self.fifo.get()

    def get_nonblocking(self):
        try:
            return self.fifo.get_nowait()
        except queue.Empty:
            return None

    def put(self, item):
        return self.fifo.put(item)

    def put_nonblocking(self, item):
        success = True
        try:
            self.fifo.put_nowait(item)
        except queue.Full:
            success = False
        return success

    def size(self):
        return self.fifo.qsize()


FriendIdentifier = str
LOOPBACK_IDENTIFIER: FriendIdentifier = "You"


class EventChatMessage:
    def __init__(self, content: str, author: FriendIdentifier, to: FriendIdentifier):
        self.content = content
        self.author = author
        self.to = to

    def is_loopback(self):
        return self.author == self.to
