from flask import Flask, request, jsonify
import httpx
import asyncio

from master.after_response import AfterResponse
from settings import slaves_ip_addresses

# app = Flask(__name__)
app = Flask("after_response")
AfterResponse(app)
MESSAGES = []


@app.route('/', methods=['POST', 'GET'])
async def main():
    if request.method == 'POST':
        try:
            write_concern: int = int(request.args.get("write_concern"))
        except (TypeError, ValueError):
            return jsonify({"message": "`write_concern` argument should be integer"})
        message: str = request.json.get("message")

        done = asyncio.Event()
        done.write_concern = write_concern

        MESSAGES.append(message)

        if write_concern == 1:
            return jsonify({"message": "successful"})

        tasks: list[asyncio.Task] = []
        for ip_address in slaves_ip_addresses():
            task = asyncio.create_task(replicate_on_slaves(ip_address, message, done))
            tasks.append(task)

        await done.wait()

        # Cancel tasks that are not finished yet
        for task in tasks:
            task.cancel()

        if done.write_concern > 1:
            return jsonify({"message": "Cannot guaranty the level of concern given"}), 400

    return ",".join(MESSAGES)


async def replicate_on_slaves(
        ip_address: str,
        message: str,
        done: asyncio.Event
):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.post(ip_address, json={"message": message})

            # Basically, the next thing is callback of a coroutine.
            done.write_concern -= 1
            if done.write_concern <= 1:
                done.set()

            return {"ip_address": f"{ip_address}", 'status': response.status_code}
        except (httpx.ConnectError, httpx.ReadTimeout):
            done.set()
            return {"ip_address": f"{ip_address}", 'status': 500}


@app.after_response
def replicate_after_response():
    for ip_address in slaves_ip_addresses():
        httpx.post(ip_address, json={"message": MESSAGES[-1]})
        # print("after_response")
