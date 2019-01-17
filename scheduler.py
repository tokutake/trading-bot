import time
import threading

class Scheduler:
    def __init__(self, func, interval):
        self.func = func
        self.interval = interval
        t = threading.Thread(target = self.start)
        t.start()

    def start(self):
        while True:
            self.func()
            time.sleep(self.interval)

