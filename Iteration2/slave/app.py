import time

from flask import Flask, request, jsonify

app = Flask(__name__)

MESSAGES = []


@app.route('/', methods=['POST', 'GET'])
def main():
    if request.method == 'POST':
        message: str = request.json.get("message")
        MESSAGES.append(message)
        delay = 0
        if not (request.json.get("delay") is None):
            delay = request.json.get("delay")
        time.sleep(delay)
    return ", ".join(MESSAGES)
