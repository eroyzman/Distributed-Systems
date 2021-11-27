import asyncio
import logging
import threading

import counter
import httpx
from flask import Flask, jsonify, request
from settings import slaves_ip_addresses

app = Flask(__name__)
MESSAGES = []
MESSAGE_ID = counter.FastWriteCounter()
MY_RETRY = 3

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/", methods=["POST", "GET"])
async def main():
    if request.method == "POST":
        try:
            write_concern: int = int(request.json.get("write_concern"))
        except (TypeError, ValueError):
            return jsonify(
                {"message": "`write_concern` argument should be integer"}
            )
        message: str = request.json.get("message")

        done = asyncio.Event()
        done.write_concern = write_concern

        MESSAGES.append(message)

        if write_concern == 1:
            for ip_address in slaves_ip_addresses():
                send_replication_request(ip_address, message, MESSAGE_ID.value)
            MESSAGE_ID.increment()
            return jsonify({"message": "successful"})

        tasks: list[tuple[asyncio.Task, str]] = []
        for ip_address in slaves_ip_addresses():
            task = asyncio.create_task(
                replicate_on_slaves(
                    ip_address, message, done, MESSAGE_ID.value
                )
            )
            logger.info(
                "Task for replication on slave:%s with ID:%d has been created",
                ip_address,
                MESSAGE_ID.value,
            )
            tasks.append((task, ip_address))

        await done.wait()

        # For tasks that were not finished we create threads in which
        # we will make new requests to slaves for replication to ensure that
        # slave has received our message.
        for task, ip_address in tasks:
            if not task.done():
                task.cancel()
                if done.write_concern > 1:
                    asyncio.create_task(
                        do_retry_request(ip_address, message, MESSAGE_ID.value)
                    )
                else:
                    send_replication_request(
                        ip_address, message, MESSAGE_ID.value
                    )
        MESSAGE_ID.increment()
    return ",".join(MESSAGES)


async def do_retry_request(ip_address: str, message: str, message_id: int):
    retry_cnt = 0
    while (retry_cnt < MY_RETRY) and (
        send_target(ip_address, message, message_id) != 200
    ):
        retry_cnt += 1
        logger.error(
            "Retried post to %s | try %d from %d",
            ip_address,
            retry_cnt,
            MY_RETRY,
        )


async def replicate_on_slaves(
    ip_address: str, message: str, done: asyncio.Event, message_id: int
):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                ip_address,
                json={"message": message, "message_id": message_id},
            )
            logger.info(
                "Response from the slave:%s with ID:%d has been received",
                ip_address,
                message_id,
            )

            # Basically, the next thing is callback of a coroutine.
            if response.status_code == 200:
                done.write_concern -= 1
            if done.write_concern <= 1:
                done.set()

            return {
                "ip_address": f"{ip_address}",
                "status": response.status_code,
            }
        except (httpx.ConnectError, httpx.ReadTimeout) as exception:
            done.set()
            logger.error(
                "Error when making request to the slave:%s with ID:%d %r, "
                "sent for retry",
                ip_address,
                message_id,
                exception,
            )
            return {"ip_address": f"{ip_address}", "status": 500}


def send_replication_request(ip_address: str, message: str, message_id: int):
    """Make replication request in the separate thread."""

    # Now we start target in the separate thread
    threading.Thread(
        target=send_target,
        args=(ip_address, message, message_id),
        daemon=True,
    ).start()


def send_target(ip_address, message, message_id):
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
