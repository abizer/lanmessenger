from enum import Enum
import queue


class EventType(Enum):
    ###########################################
    # New friend discovered in the LAN
    # Friend is either online, away, offline
    FRIEND_STATUS_CHANGED = (1,)
    # Message came in over the network
    MESSAGE_RECEIVED = (2,)

    ###########################################
    # Send message over the network
    MESSAGE_SENT = (3,)


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


class ChatMessagePayload:
    def __init__(self, content: str, author: FriendIdentifier, to: FriendIdentifier):
        self.content = content
        self.author = author
        self.to = to

    def is_loopback(self):
        return self.author == self.to


class Status(Enum):
    # Sending discovery pings and activity pings within past 15 minutes
    ONLINE = 1
    # Sending discovery pings but no recent activity pings
    AWAY = 2
    # Not sending discovery pings
    OFFLINE = 3


class StatusChangedPayload:
    def __init__(self, id: FriendIdentifier, status: Status):
        self.id = id
        self.status = status
