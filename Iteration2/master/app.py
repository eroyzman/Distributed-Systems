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
                threading.Thread(
                    target=send_replication_request,
                    kwargs={
                        "ip_address": ip_address,
                        "message": message,
                        "timestamp": timestamp,
                    },
                    daemon=True,
                ).start()
            return jsonify({"message": "successful"})

        tasks: list[asyncio.Task] = []
        for ip_address in slaves_ip_addresses():
            task = asyncio.create_task(
                replicate_on_slaves(ip_address, message, timestamp, done)
            )
            logger.info(
                "Task for replication on slave:%s has been created",
                ip_address,
            )
            tasks.append(task)

        await done.wait()

        # Cancel tasks that are not finished yet
        for task in tasks:
            task.cancel()

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
        except (httpx.ConnectError, httpx.ReadTimeout):
            done.set()
            logger.error(
                "Error when making request to the slave:%s",
                ip_address,
                exc_info=True,
            )
            return {"ip_address": f"{ip_address}", "status": 500}


def send_replication_request(ip_address: str, message: str, timestamp: float):
    with httpx.Client() as client:
        try:
            client.post(
                ip_address, json={"message": message, "timestamp": timestamp}
            )
            logger.info(
                "Response from the slave:%s has been received",
                ip_address,
            )
        except (httpx.ConnectError, httpx.ReadTimeout):
            logger.error(
                "Error when making request to the slave:%s",
                ip_address,
                exc_info=True,
            )
