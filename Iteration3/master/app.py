import threading
import logging
import asyncio

import counter
from flask import Flask, jsonify, request

from settings import END_RANGE, START_RANGE, slaves_ip_addresses
from annotations import Message
from healthchecks import check_secondaries, check_all_healthy
from replication import replicate_message_on_slaves

MESSAGES: list[Message] = []
MESSAGE_ID = counter.FastWriteCounter()
MY_RETRY = 3
RETRY_WAIT = 10
QUORUM = (END_RANGE - START_RANGE + 1) // 2 + 1
app = Flask(__name__)

logging.basicConfig(
    format="time: %(asctime)s - line: %(lineno)d - message: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def wrapper():
    """Wrapper function for the heartbeat functionality."""
    async def run_heartbeat():
        logger.info("Heartbeat process started")
        current_message_id = MESSAGE_ID.value
        result = {}

        while True:
            if MESSAGE_ID.value != current_message_id or not check_all_healthy(result):
                logger.info("Making heartbeat requests ...")
                current_message_id = MESSAGE_ID.value
                result, _ = await check_secondaries(MESSAGES)
                logger.info("Heartbeat checks finished")
            await asyncio.sleep(20)

    asyncio.run(run_heartbeat())


threading.Thread(
    target=wrapper,
    daemon=True,
).start()


@app.route("/", methods=["POST", "GET"])
async def main():
    if request.method == "POST":
        try:
            write_concern: int = int(request.json.get("write_concern"))
        except (TypeError, ValueError):
            return jsonify(
                {"message": "`write_concern` argument should be integer"}
            )
        message_body: str = request.json.get("message")

        # First we check secondaries, if they have all messages replicated.
        # If not - we send missing messages to them.
        _, slaves_alive = await check_secondaries(MESSAGES)

        if slaves_alive + 1 < QUORUM:
            return f"Too few servers:{slaves_alive}, less then QUORUM:{QUORUM}"

        MESSAGE_ID.increment()
        MESSAGES.append(Message(MESSAGE_ID.value, message_body))

        await replicate_message_on_slaves(
            message_body, slaves_ip_addresses(), MESSAGE_ID.value, write_concern
        )

    return ", ".join(message.body for message in MESSAGES)


@app.route("/health", methods=["GET"])
async def get_health_status():
    result, _ = await check_secondaries(MESSAGES)
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




