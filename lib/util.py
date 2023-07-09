import queue


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
