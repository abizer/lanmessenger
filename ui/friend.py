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

    def __init__(self, username, status=Status.ONLINE):
        self.username = username
        self.status = status
        self.has_unread = False

    def __hash__(self):
        return hash(self.username)

    def __eq__(self, other):
        if other == None:
            return False
        return self.username == other.username


FRIEND_LOOPBACK = Friend("You")


class Message:
    def __init__(self, content: str, author: Friend, to: Friend):
        self.content = content
        self.author = author
        self.to = to

    def is_loopback(self):
        return self.author == self.to
