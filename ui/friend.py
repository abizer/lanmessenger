from enum import Enum
import uuid


class Friend:
    class Status(Enum):
        # Sending discovery pings and activity pings within past 15 minutes
        ONLINE = 1
        # Sending discovery pings but no recent activity pings
        AWAY = 2
        # Not sending discovery pings
        OFFLINE = 3

    def __init__(self, username, uuid=uuid.uuid4(), status=Status.ONLINE):
        self.username = username
        self.status = status
        self.uuid = uuid

    def __hash__(self):
        return hash(self.uuid)

    def __eq__(self, other):
        return self.username == other.username and self.uuid == other.uuid


FRIEND_LOOPBACK = Friend("You")


class Message:
    def __init__(self, content: str, author: Friend, to: Friend):
        self.content = content
        self.author = author
        self.to = to

    def is_loopback(self):
        return self.author == self.to
