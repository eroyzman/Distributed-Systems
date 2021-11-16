import time

from flask import Flask, request

app = Flask(__name__)

MESSAGES = []


@app.route('/', methods=['POST', 'GET'])
def main():
    if request.method == 'POST':
        message: str = request.json.get("message")
        MESSAGES.append(message)

        if delay := request.json.get("delay"):
            time.sleep(delay)

        time.sleep(0)

    return ", ".join(MESSAGES)
