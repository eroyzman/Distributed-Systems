import logging
import threading

import httpx
from settings import slaves_ip_addresses
from replication import do_retry_request


logging.basicConfig(
    format="time: %(asctime)s - line: %(lineno)d - message: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


async def check_secondaries(messages: list[tuple[int, str]]):
    result, alive_slaves = {}, 0
    async with httpx.AsyncClient() as client:
        for ip_address in slaves_ip_addresses():
            try:
                response = await client.get(ip_address + "health")
                response_result = response.json()

                if response_result["health"] == "Suspected":
                    send_missing_messages(
                        ip_address, response_result["suspected_messages"], messages
                    )

                result[ip_address] = response.json()
                alive_slaves += 1
            except (httpx.ConnectError, httpx.ReadTimeout) as exception:
                logger.error(
                    "Error when making check request to the slave:%s with %r, "
                    "scheduled for the retry",
                    ip_address,
                    exception,
                )
                result[ip_address] = {"health": "Suspected", "status": 500}

    return result, alive_slaves


def send_missing_messages(
    ip_address,
    missing_message_ids: list[int],
    messages: list[tuple[int, str]]
):
    logger.info(
        "Sending messages:%s for the %s that might have missed it",
        missing_message_ids,
        ip_address
    )
    for missing_message in filter(
        lambda m: m[0] in missing_message_ids, messages
    ):
        threading.Thread(
            target=do_retry_request,
            args=(ip_address, missing_message, missing_message[0]),
            daemon=True,
        ).start()
