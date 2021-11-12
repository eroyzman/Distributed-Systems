from typing import Iterator

from environs import Env

env = Env()

START_RANGE = env.int("START_RANGE", 6001)
END_RANGE = env.int("END_RANGE", 6004)
LOCALHOST = env.str("LOCALHOST", "http://127.0.0.1")


def slaves_ip_addresses() -> Iterator[str]:
    for idx, port in enumerate(range(START_RANGE, END_RANGE), start=1):
        if LOCALHOST == "http://127.0.0.1":
            yield f"{LOCALHOST}:{port}/"
        else:
            yield f"http://slave_{idx}:5000/"
