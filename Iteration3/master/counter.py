# https://github.com/jd/fastcounter
import itertools
import threading


class Counter:
    __slots__ = (
        "value",
        "_step",
    )

    def __init__(self, init=0, step=1):
        self.value = init
        self._step = step

    def increment(self, num_steps=1):
        self.value += self._step * num_steps


class FastWriteCounter(Counter):
    __slots__ = (
        "_number_of_read",
        "_counter",
        "_lock",
        "_step",
    )

    def __init__(self, init=-1, step=1):
        self._number_of_read = 0
        self._step = step
        self._counter = itertools.count(init, step)
        self._lock = threading.Lock()

    def increment(self, num_steps=1):
        with self._lock:
            for _i in range(num_steps):
                next(self._counter)

    @property
    def value(self):
        with self._lock:
            value = next(self._counter) - self._number_of_read
            self._number_of_read += self._step
        return value
