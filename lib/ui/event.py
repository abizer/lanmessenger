from dataclasses import dataclass
from enum import IntEnum
from typing import Union


class EventType(IntEnum):
    ###########################################
    # New friend discovered in the LAN
    # Friend is either online, away, offline
    FRIEND_STATUS_CHANGED = 1
    # Message came in over the network
    MESSAGE_RECEIVED = 2

    ###########################################
    # Send message over the network
    MESSAGE_SENT = 3
    # Username changed
    USERNAME_CHANGED = 4
    # Username request
    USERNAME_REQUEST = 5


FriendIdentifier = str
LOOPBACK_IDENTIFIER: FriendIdentifier = "You"


@dataclass
class ChatMessagePayload:
    content: str
    author: FriendIdentifier
    to: FriendIdentifier

    def is_loopback(self):
        return self.author == self.to


class Status(IntEnum):
    # Sending discovery pings and activity pings within past 15 minutes
    ONLINE = 1
    # Sending discovery pings but no recent activity pings
    AWAY = 2
    # Not sending discovery pings
    OFFLINE = 3


@dataclass
class StatusChangedPayload:
    id: FriendIdentifier
    status: Status


@dataclass
class UsernameChangedPayload:
    id: FriendIdentifier
    username: str


UiEventPayload = Union[ChatMessagePayload, StatusChangedPayload, UsernameChangedPayload]


@dataclass
class EventMessage:
    type: EventType
    payload: UiEventPayload
