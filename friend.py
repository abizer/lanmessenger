from collections import OrderedDict
from enum import Enum
import random
import uuid

ENABLE_MOCK_DATA = True

class Friend:
    class Status(Enum):
        # Sending discovery pings and activity pings within past 15 minutes
        ONLINE = 1   
        # Sending discovery pings but no recent activity pings
        AWAY   = 2 
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

class Message:
    def __init__(self, content, outgoing):
        self.content = content
        self.outgoing = outgoing


MOCK_FRIENDS = OrderedDict()
MOCK_FRIENDS[Friend("Abizer")] = []
MOCK_FRIENDS[Friend("Liam")] = []
MOCK_FRIENDS[Friend("Rachel")] = []

if ENABLE_MOCK_DATA:
    def populate_mock_data():
        stub_text = []
        with open("declaration.txt") as f:
            for line in f.readlines():
                l = line.strip()
                if len(l) > 0:
                    stub_text.append(l)

        max_line = len(stub_text)

        for friend, message_buffer in MOCK_FRIENDS.items():
            sent_start = random.randrange(0, max_line-1)
            recv_start = random.randrange(0, max_line-1)

            outgoing = [ Message(d, True) for d in stub_text[sent_start:sent_start+15] ]
            incoming = [ Message(d, False) for d in stub_text[recv_start:recv_start+15] ]
            while len(outgoing) > 0 and len(incoming) > 0:
                if random.random() > 0.5:
                    MOCK_FRIENDS[friend].append(outgoing.pop())
                else:
                    MOCK_FRIENDS[friend].append(incoming.pop())
            while len(incoming) > 0:
                    MOCK_FRIENDS[friend].append(incoming.pop())
            while len(outgoing) > 0:
                    MOCK_FRIENDS[friend].append(outgoing.pop())
    
    populate_mock_data()

