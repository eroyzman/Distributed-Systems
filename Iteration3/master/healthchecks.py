from __future__ import annotations

import logging
import threading

import httpx
from settings import slaves_ip_addresses

logging.basicConfig(
    format="time: %(asctime)s - line: %(lineno)d - message: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class SlavesInspector:
    def __init__(self):
        self.slave_statuses = {}
        self._lock = threading.Lock()

    def set_slave_status(self, slave_ip: str, status: str):
        self.slave_statuses[slave_ip] = status

    @property
    def slaves_alive(self) -> list[str]:
        return [
            ip_address
            for ip_address, status in self.slave_statuses.items()
            if status == "Healthy"
        ]

    @property
    def slaves_alive_num(self) -> int:
        return len(self.slaves_alive)

    def __len__(self):
        return len(self.slave_statuses)


async def check_secondaries(timeout: float = 1) -> SlavesInspector:
    slaves_inspector = SlavesInspector()

    async with httpx.AsyncClient(timeout=timeout) as client:
        for ip_address in slaves_ip_addresses():
            try:
                logger.info(
                    f"Sending heartbeat to the ip_address:{ip_address}"
                )
                response = await client.get(ip_address)
                response_result = response.json()
                logger.info(
                    f"Response from the slave:{ip_address} has been received: {response_result}"
                )

                slaves_inspector.set_slave_status(ip_address, "Healthy")
            except (httpx.ConnectError, httpx.ReadTimeout) as exception:
                logger.error(
                    "Error when making check request to the slave:%s with %r",
                    ip_address,
                    exception,
                )
                slaves_inspector.set_slave_status(ip_address, "Suspected")

    return slaves_inspector
