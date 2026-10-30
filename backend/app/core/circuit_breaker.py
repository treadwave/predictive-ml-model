import logging
import time

logger = logging.getLogger("circuit_breaker")

class CircuitBreaker:
    def __init__(self, error_threesold, time):
        self.errors = 0
        self.time_begin = 0
        self.time_to_wait = time
        self.state = "closed"
        self.error_threesold = error_threesold

    def errors_counter(self):
        self.errors += 1

        if self.errors >= self.error_threesold:
            self.time_begin = time.time()
            self.time_wait = self.time_begin + self.time_to_wait
            self.open()

    def open(self):
        self.state = "open"
        self.errors = 0
        logger.info("Circuit breaker opened")

    def reset(self):
        self.errors = 0
        self.state = "closed"

    def set_closed(self):
        self.set_state("closed")
        self.errors = 0

    def half_open(self):
        self.errors = 0
        self.state = "half-open"
        self.time_begin = time.time()
        self.time_wait = self.time_begin + self.time_to_wait

    def check_time(self):
        self.time_begin = time.time()
        if (self.time_begin >= self.time_wait):
            self.half_open()

    def allow_request(self) -> bool:
        if self.state == "open":
            self.check_time()

        if self.state == "open":
            return False

        if self.state == "closed" or self.state == "half-open":
            return True

    def set_state(self, val=str):
        self.state = val

    def check_half_open(self):
        if self.state == "half-open":
            self.open()


circuit_breaker = CircuitBreaker(error_threesold=3, time=60)