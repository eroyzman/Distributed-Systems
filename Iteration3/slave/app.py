import logging
import time

from flask import Flask, jsonify, request
from settings import DELAY
from storage import MessageStorage

app = Flask(__name__)

logging.basicConfig(
    format="time: %(asctime)s - message: %(message)s - line: %(lineno)d",
    level=logging.INFO,
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


@app.route("/", methods=["POST", "GET"])
def main():
    if request.method == "POST":
        message: str = request.json.get("message")
        message_id: int = int(request.json.get("message_id"))
        logger.info("Message with ID:%d has been received", message_id)

        time.sleep(DELAY)
        MessageStorage.insert_message(message, message_id)

    return MessageStorage.get_messages()


@app.route("/health", methods=["GET"])
def get_health_status():
    suspected_messages = MessageStorage.get_missing_messages()
    if suspected_messages:
        return jsonify(
            {"health": "Suspected", "suspected_messages": suspected_messages}
        )

    return jsonify({"health": "Healthy"})
