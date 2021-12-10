import asyncio
import logging
import threading

import counter
from annotations import Message
from flask import Flask, jsonify, request
from healthchecks import SlavesInspector, check_secondaries
from replication import replicate_message_on_slaves
from settings import HEARTBEAT_RATE, QUORUM

MESSAGES: list[Message] = []
MESSAGE_ID = counter.FastWriteCounter()
SLAVES_INSPECTOR = SlavesInspector()

app = Flask(__name__)

logging.basicConfig(
    format="time: %(asctime)s - line: %(lineno)d - message: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def heartbeat_wrapper():
    """Wrapper function for the heartbeat functionality."""

    async def run_heartbeat():
        logger.info("Heartbeat process started")
        while True:
            logger.info("Making heartbeat requests ...")
            await check_secondaries(SLAVES_INSPECTOR)
            logger.info("Heartbeat checks finished")
            await asyncio.sleep(60 / HEARTBEAT_RATE)

    asyncio.run(run_heartbeat())


threading.Thread(
    target=heartbeat_wrapper,
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

        if alive_slaves := (SLAVES_INSPECTOR.slaves_alive_num + 1) < QUORUM:
            return f"Too few servers:{alive_slaves}, less then QUORUM:{QUORUM}"

        MESSAGE_ID.increment()
        MESSAGES.append(Message(MESSAGE_ID.value, message_body))

        await replicate_message_on_slaves(
            MESSAGE_ID.value,
            MESSAGES,
            SLAVES_INSPECTOR,
            write_concern,
        )

    return ", ".join(message.body for message in MESSAGES)
