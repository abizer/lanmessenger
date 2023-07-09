from enum import Enum


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
