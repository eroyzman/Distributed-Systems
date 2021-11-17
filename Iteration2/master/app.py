import asyncio
import logging
import threading
import time

import httpx
from flask import Flask, jsonify, request
from settings import slaves_ip_addresses

app = Flask(__name__)
MESSAGES = []

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/", methods=["POST", "GET"])
async def main():
    if request.method == "POST":
        try:
            write_concern: int = int(request.args.get("write_concern"))
        except (TypeError, ValueError):
            return jsonify(
                {"message": "`write_concern` argument should be integer"}
            )
        message: str = request.json.get("message")

        done = asyncio.Event()
        done.write_concern = write_concern
        timestamp = time.time()

        MESSAGES.append(message)

        if write_concern == 1:
            for ip_address in slaves_ip_addresses():
                send_replication_request(ip_address, message, timestamp)
            return jsonify({"message": "successful"})

        tasks: list[tuple[asyncio.Task, str]] = []
        for ip_address in slaves_ip_addresses():
            task = asyncio.create_task(
                replicate_on_slaves(ip_address, message, timestamp, done)
            )
            logger.info(
                "Task for replication on slave:%s has been created",
                ip_address,
            )
            tasks.append((task, ip_address))

        await done.wait()

        # For tasks that were not finished we create threads in which
        # we will make new requests to slaves for replication to ensure that
        # slave has received our message.
        for task, ip_address in tasks:
            if not task.done():
                task.cancel()
                send_replication_request(ip_address, message, timestamp)

        if done.write_concern > 1:
            return (
                jsonify(
                    {"message": "Cannot guaranty the level of concern given"}
                ),
                400,
            )

    return ",".join(MESSAGES)


async def replicate_on_slaves(
    ip_address: str, message: str, timestamp: float, done: asyncio.Event
):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.post(
                ip_address, json={"message": message, "timestamp": timestamp}
            )
            logger.info(
                "Response from the slave:%s has been received",
                ip_address,
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
                "Error when making request to the slave:%s %r",
                ip_address,
                exception,
            )
            return {"ip_address": f"{ip_address}", "status": 500}


def send_replication_request(ip_address: str, message: str, timestamp: float):
    """Make replication request in the separate thread."""

    def target():
        with httpx.Client(timeout=60) as client:
            try:
                logger.info(
                    "Sending replication request to the slave:%s",
                    ip_address,
                )
                client.post(
                    ip_address,
                    json={"message": message, "timestamp": timestamp},
                )
                logger.info(
                    "Response from the slave:%s has been received",
                    ip_address,
                )
            except (httpx.ConnectError, httpx.ReadTimeout) as exception:
                logger.error(
                    "Error when making request to the slave:%s %r",
                    ip_address,
                    exception,
                )

    # Now we start target in the separate thread
    threading.Thread(
        target=target,
        daemon=True,
    ).start()
