from friend import Friend, Message
from time import sleep
from comms import EventMessage, EventQueue, EventType
import random
import re
import pathlib

DIR = pathlib.Path(__file__).parent

alphabets = "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|edu|me)"
digits = "([0-9])"
multiple_dots = r"\.{2,}"


def split_into_sentences(text: str) -> list[str]:
    """
    Split the text into sentences.

    If the text contains substrings "<prd>" or "<stop>", they would lead
    to incorrect splitting because they are used as markers for splitting.

    :param text: text to be split into sentences
    :type text: str

    :return: list of sentences
    :rtype: list[str]
    """
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    text = re.sub(digits + "[.]" + digits, "\\1<prd>\\2", text)
    text = re.sub(
        multiple_dots, lambda match: "<prd>" * len(match.group(0)) + "<stop>", text
    )
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub("\s" + alphabets + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
    text = re.sub(
        alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]",
        "\\1<prd>\\2<prd>\\3<prd>",
        text,
    )
    text = re.sub(alphabets + "[.]" + alphabets + "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
    text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
    text = re.sub(" " + alphabets + "[.]", " \\1<prd>", text)
    if "”" in text:
        text = text.replace(".”", "”.")
    if '"' in text:
        text = text.replace('."', '".')
    if "!" in text:
        text = text.replace('!"', '"!')
    if "?" in text:
        text = text.replace('?"', '"?')
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = [s.strip() for s in sentences]
    if sentences and not sentences[-1]:
        sentences = sentences[:-1]
    return sentences


mock_sentences = []


def generate_mocked_message():
    global mock_sentences
    if len(mock_sentences) == 0:
        data_path = DIR / "data" / "declaration.txt"
        with open(data_path) as f:
            mock_sentences = split_into_sentences(f.read())

    assert len(mock_sentences) != 0
    last_sentence = len(mock_sentences)
    return mock_sentences[random.randrange(0, last_sentence - 1)]


def mock_network_events(tx_queue: EventQueue, rx_queue: EventQueue):
    # Seed friend discovery
    print(generate_mocked_message())
    for name in ("Abizer", "Daniel", "Liam", "Rachel"):
        sleep(random.randrange(1, 3))
        tx_queue.put(
            EventMessage(type=EventType.FRIEND_DISCOVERED, payload=Friend(name))
        )

    while True:
        msg = rx_queue.get()
        if msg.type == EventType.MESSAGE_SENT:
            m = msg.payload
            print(f"MOCK SENT MESSAGE: TO={m.to.username} Content: {m.content}")
            if not m.is_loopback():
                sleep(random.randrange(1, 3))
                response = Message(generate_mocked_message(), author=m.to, to=m.author)
                tx_queue.put(
                    EventMessage(type=EventType.MESSAGE_RECEIVED, payload=response)
                )
