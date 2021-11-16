import time

from flask import Flask, request

app = Flask(__name__)

MESSAGES = []


@app.route("/", methods=["POST", "GET"])
def main():
    if request.method == "POST":
        message: str = request.json.get("message")
        timestamp: float = float(request.json.get("timestamp"))
        insert_message(message, timestamp)

        if delay := request.json.get("delay"):
            time.sleep(delay)

    return ", ".join(message[0] for message in MESSAGES)


def insert_message(message: str, timestamp: float) -> None:
    # Messages deduplication
    if message in {item[0] for item in MESSAGES}:
        return

    MESSAGES.append((message, timestamp))
    # Sort messages by timestamp
    MESSAGES.sort(key=lambda x: x[1])
