import asyncio
import logging
import threading

import counter
import httpx
from flask import Flask, jsonify, request
from settings import END_RANGE, START_RANGE, slaves_ip_addresses

app = Flask(__name__)
MESSAGES = []
MESSAGE_ID = counter.FastWriteCounter()
MY_RETRY = 3
QUORUM = int((len(range(START_RANGE, END_RANGE)) + 1) / 2) + 1

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

        result = await check_secondaries()
        success_cnt = len(
            [
                ip_address
                for ip_address in result
                if result[ip_address]["health"] == "Healthy"
            ]
        )

        if success_cnt < QUORUM:
            return "Too few servers, less then QUORUM"

        MESSAGES.append([MESSAGE_ID.value, message])

        if write_concern == 1:
            for ip_address in slaves_ip_addresses():
                send_replication_request(
                    send_message, ip_address, message, MESSAGE_ID.value
                )
            MESSAGE_ID.increment()
            return jsonify({"message": "successful"})

        message_id = MESSAGE_ID.value
        MESSAGE_ID.increment()
        await send_message_to_secondaries(
            message, slaves_ip_addresses(), message_id, write_concern
        )

    return ",".join([message[1] for message in MESSAGES])


@app.route("/health", methods=["GET"])
async def get_health_status():
    result = await check_secondaries()
    return str(result)


@app.route("/quorum", methods=["POST", "GET"])
async def quorum():
    global QUORUM
    if request.method == "POST":
        try:
            QUORUM = int(request.json.get("quorum"))
        except (TypeError, ValueError):
            return jsonify({"message": "`quorum` argument should be integer"})

    return str(QUORUM)


async def check_secondaries():
    result = {}
    async with httpx.AsyncClient() as client:
        for ip_address in slaves_ip_addresses():
            try:
                response = await client.get(ip_address + "health")

                response_result = response.json()

                if response_result["health"] == "Suspected":
                    send_suspected_messages(
                        ip_address, response_result["suspected_messages"]
                    )

                result[ip_address] = response.json()
            except (httpx.ConnectError, httpx.ReadTimeout) as exception:
                logger.error(
                    "Error when making request to the slave:%s with %r, "
                    "scheduled for the retry",
                    ip_address,
                    exception,
                )
                result[ip_address] = {"health": "Suspected", "status": 500}

    return result


def send_suspected_messages(ip_address, suspected_messages):
    for suspected_message_id in suspected_messages:
        threading.Thread(
            target=send_suspected_message,
            args=(ip_address, suspected_message_id),
            daemon=True,
        ).start()


def send_suspected_message(ip_address, suspected_message_id):
    for message in MESSAGES:
        if message[0] == suspected_message_id:
            send_message_to_secondaries(
                message[1], [ip_address], suspected_message_id, 2
            )
            return


async def send_message_to_secondaries(
    message, secondaries, message_id, write_concern
):
    done = asyncio.Event()
    done.write_concern = write_concern

    common_tasks: list[tuple[asyncio.Task, str]] = []
    for ip_address in secondaries:
        task = asyncio.create_task(
            replicate_on_slaves(ip_address, message, done, message_id)
        )
        logger.info(
            "Task for replication on slave:%s with ID:%d has been created",
            ip_address,
            message_id,
        )
        common_tasks.append((task, ip_address))

    await done.wait()

    # For tasks that were not finished we create threads in which
    # we will make new requests to slaves for replication to ensure that
    # slave has received our message.
    if done.write_concern > 1:
        for task, ip_address in common_tasks:
            if not task.done():
                send_replication_request(
                    do_retry_request, ip_address, message, MESSAGE_ID.value
                )


def do_retry_request(ip_address, message, message_id):
    attempts_cnt = 0
    while (attempts_cnt <= MY_RETRY) and (
        send_message(ip_address, message, message_id) != 200
    ):
        if attempts_cnt != 0:
            logger.error(
                "Retried post to %s | try %d from %d",
                ip_address,
                attempts_cnt,
                MY_RETRY,
            )
        attempts_cnt += 1


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


def send_replication_request(
    func, ip_address: str, message: str, message_id: int
):
    """Make replication request in the separate thread."""

    # Now we start target in the separate thread
    threading.Thread(
        target=func,
        args=(ip_address, message, message_id),
        daemon=True,
    ).start()


def send_message(ip_address, message, message_id):
    with httpx.Client(timeout=5) as client:
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
