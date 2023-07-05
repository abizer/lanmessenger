from friend import Friend
from time import sleep
from comms import EventMessage, EventQueue, EventType
import comms
import random
import pathlib

DIR = pathlib.Path(__file__).parent


def populate_mock_data():
    stub_text = []
    data_path = DIR / "data" / "declaration.txt"
    with open(data_path) as f:
        for line in f.readlines():
            l = line.strip()
            if len(l) > 0:
                stub_text.append(l)

    max_line = len(stub_text)

    for friend, message_buffer in MOCK_FRIENDS.items():
        sent_start = random.randrange(0, max_line - 1)
        recv_start = random.randrange(0, max_line - 1)

        outgoing = [Message(d, True) for d in stub_text[sent_start : sent_start + 15]]
        incoming = [Message(d, False) for d in stub_text[recv_start : recv_start + 15]]
        while len(outgoing) > 0 and len(incoming) > 0:
            if random.random() > 0.5:
                MOCK_FRIENDS[friend].append(outgoing.pop())
            else:
                MOCK_FRIENDS[friend].append(incoming.pop())
        while len(incoming) > 0:
            MOCK_FRIENDS[friend].append(incoming.pop())
        while len(outgoing) > 0:
            MOCK_FRIENDS[friend].append(outgoing.pop())


def mock_network_events(tx_queue: EventQueue, rx_queue: EventQueue):
    # Seed friend discovery
    for name in ("Abizer", "Liam", "Rachel"):
        sleep(random.randrange(1, 3))
        tx_queue.put(
            EventMessage(type=EventType.FRIEND_DISCOVERED, payload=Friend(name))
        )

    while True:
        msg = rx_queue.get()
        if msg.type == EventType.MESSAGE_SENT:
            m = msg.payload
            print(f"MOCK SENT MESSAGE: TO=FIXME Content: {m.content}"),
