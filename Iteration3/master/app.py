import logging

import counter
from flask import Flask, jsonify, request
from settings import END_RANGE, START_RANGE, slaves_ip_addresses
from healthchecks import check_secondaries
from replication import run_in_daemon_thread, replicate_message_on_slaves, send_message

MESSAGES = []
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

        # First we check secondaries, if they have all messages replicated.
        # If not - we send missing messages to them.
        _, slaves_alive = await check_secondaries(MESSAGES)

        if slaves_alive < QUORUM:
            return f"Too few servers:{slaves_alive}, less then QUORUM:{QUORUM}"

        MESSAGE_ID.increment()
        MESSAGES.append([MESSAGE_ID.value, message])

        if write_concern == 1:
            for ip_address in slaves_ip_addresses():
                run_in_daemon_thread(
                    send_message, ip_address, message, MESSAGE_ID.value
                )
            return jsonify({"message": "successful"})

        if not await replicate_message_on_slaves(
            message, slaves_ip_addresses(), MESSAGE_ID.value, write_concern
        ):
            return jsonify({"message": "Cannot guaranty level of concern given"})

    return ",".join([message[1] for message in MESSAGES])


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



