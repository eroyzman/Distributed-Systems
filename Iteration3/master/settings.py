from functools import lru_cache

from environs import Env

env = Env()

START_RANGE = env.int("START_RANGE", 6001)
END_RANGE = env.int("END_RANGE", 6004)
LOCALHOST = env.str("LOCALHOST", "http://127.0.0.1")


@lru_cache(maxsize=None)
def slaves_ip_addresses() -> list[str]:
    ip_addresses = []
    for idx, port in enumerate(range(START_RANGE, END_RANGE), start=1):
        if LOCALHOST == "http://127.0.0.1":
            address = f"{LOCALHOST}:{port}/"
        else:
            address = f"http://slave_{idx}:5000/"
        ip_addresses.append(address)
    return ip_addresses
