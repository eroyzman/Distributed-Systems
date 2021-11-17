import logging
import time

from flask import Flask, request
from settings import DELAY
from storage import MessageStorage

app = Flask(__name__)

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/", methods=["POST", "GET"])
def main():
    if request.method == "POST":
        logger.info("Message has been received")
        message: str = request.json.get("message")
        timestamp: float = float(request.json.get("timestamp"))

        time.sleep(DELAY)
        MessageStorage.insert_message(message, timestamp)

    return MessageStorage.messages()
