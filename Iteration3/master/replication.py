from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app import Message
    from healthchecks import SlavesInspector

MY_RETRY = 3
RETRY_WAIT = 10

logging.basicConfig(
    format="time: %(asctime)s - line: %(lineno)d - message: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def send_message_to_slave_initial(
    messages: list[Message],
    message_id: int,
    done: asyncio.Event,
    ip_address: str,
):
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            response = await client.post(
                ip_address,
                json={
                    "message": messages[message_id].body,
                    "message_id": message_id,
                },
            )
            logger.info(
                "Response from the slave:%s with ID:%d has been received",
                ip_address,
                message_id,
            )
        except httpx.ConnectError as exception:
            logger.error(
                "Error when making request to the slave:%s with ID:%d %r, "
                "scheduled for the retry",
                ip_address,
                message_id,
                exception,
            )
            return {"ip_address": ip_address, "status": 500}
        else:
            if response.status_code == 200:
                done.write_concern -= 1
            if done.write_concern <= 1:
                done.set()

            return {
                "ip_address": ip_address,
                "status": response.status_code,
            }


def run_in_daemon_thread(
    ip_address: str,
    message: str,
    message_id: int,
    slaves_inspector: SlavesInspector = None,
):
    """Make replication request in the separate thread."""

    def do_retry_request(ip_address: str, message: str, message_id: int):
        attempts_cnt = 0
        waiting_seconds = 0
        response = 0

        while response != 200:
            while not slaves_inspector.is_alive(ip_address):
                #  Wait for node to be again alive
                time.sleep(10)
                waiting_seconds += 10
                logger.info(
                    "Waiting for the slave: %s to be alive for the %d seconds",
                    ip_address,
                    waiting_seconds,
                )

            while (
                slaves_inspector.is_alive(ip_address)
                and (response := send_message(ip_address, message, message_id))
                != 200
            ):
                if attempts_cnt != 0:
                    logger.error(
                        "Retried post to %s | try %d from %d",
                        ip_address,
                        attempts_cnt,
                        MY_RETRY,
                    )
                attempts_cnt += 1

    # Now we start target in the separate thread
    threading.Thread(
        target=do_retry_request,
        args=(ip_address, message, message_id),
        daemon=True,
    ).start()


def send_message(ip_address, message, message_id) -> int:
    with httpx.Client(timeout=10) as client:
        try:
            logger.info(
                "Sending replication request to the slave:%s with ID:%d",
                ip_address,
                message_id,
            )
            response = client.post(
                ip_address,
                json={"message": message, "message_id": message_id},
            )
            logger.info(
                "Response from the slave:%s with ID:%d has been received",
                ip_address,
                message_id,
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as exception:
            logger.error(
                "Error when making request to the slave:%s with ID:%d %r",
                ip_address,
                message_id,
                exception,
            )
            return 500
    return response.status_code


async def replicate_message_on_slaves(
    message_id: int,
    messages: list[Message],
    slave_inspector: SlavesInspector,
    write_concern: int,
) -> None:
    done = asyncio.Event()
    done.write_concern = write_concern

    common_tasks: list[tuple[asyncio.Task, str]] = []
    for ip_address in slave_inspector.slaves_alive:
        task = asyncio.create_task(
            send_message_to_slave_initial(
                messages, message_id, done, ip_address
            )
        )
        common_tasks.append((task, ip_address))
        logger.info(
            "Task for replication on slave:%s with ID:%d has been created",
            ip_address,
            message_id,
        )

    if write_concern > 1:
        await done.wait()
    # For tasks that were not finished we create threads in which
    # we will make new requests to slaves for replication to ensure that
    # slave has received our message.
    for task, ip_address in common_tasks:
        if not task.done() or (task.done() and task.result()["status"] != 200):
            task.cancel()
            run_in_daemon_thread(
                ip_address,
                messages[message_id].body,
                message_id,
                slave_inspector,
            )

    # Also schedule replication of the message on the dead slaves
    for ip_address in slave_inspector.slaves_dead:
        run_in_daemon_thread(
            ip_address,
            messages[message_id].body,
            message_id,
            slave_inspector,
        )
