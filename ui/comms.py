from enum import Enum
from friend import Friend
import queue

class EventType(Enum):
    # New friend discovered in the LAN
    FRIEND_DISCOVERED     = 1,
    # Friend is either online, away, offline
    FRIEND_STATUS_CHANGED = 2,
    # Message came in over the network
    MESSAGE_RECEIVED      = 3,

class EventMessage():
    def __init__(self, type, payload):
        self.type    = type
        self.payload = payload

class EventQueue:
   def __init__(self):
      self.fifo = queue.Queue()

   # get is always nonblocking so we don't lock up the UI thread
   def get(self):
      try:
         return self.fifo.get_nowait()
      except queue.Empty:
         return None

   # put can be blocking
   def put(self, item):
      return self.fifo.put(item)

   def size(self):
      return self.fifo.qsize()
