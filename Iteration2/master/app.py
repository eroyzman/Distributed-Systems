import asyncio
import time

import httpx
from flask import Flask, jsonify, request
from settings import slaves_ip_addresses

app = Flask(__name__)
MESSAGES = []


@app.route("/", methods=["POST", "GET"])
async def main():
    if request.method == "POST":
        try:
            write_concern: int = int(request.args.get("write_concern"))
        except (TypeError, ValueError):
            return jsonify(
                {"message": "`write_concern` argument should be integer"}
            )
        message: str = request.json.get("message")
        timestamp = time.time()

        done = asyncio.Event()
        done.write_concern = write_concern

        MESSAGES.append(message)

        tasks: list[asyncio.Task] = []
        for ip_address in slaves_ip_addresses():
            task = asyncio.create_task(
                replicate_on_slaves(ip_address, message, timestamp, done)
            )
            tasks.append(task)

        await done.wait()

        # Cancel tasks that are not finished yet
        for task in tasks:
            task.cancel()

        if done.write_concern > 1:
            return (
                jsonify(
                    {"message": "Cannot guaranty the level of concern given"}
                ),
                400,
            )

    return ",".join(MESSAGES)


async def replicate_on_slaves(
    ip_address: str, message: str, timestamp: float, done: asyncio.Event
):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.post(
                ip_address, json={"message": message, "timestamp": timestamp}
            )

            # Basically, the next thing is callback of a coroutine.
            done.write_concern -= 1
            if done.write_concern <= 1:
                done.set()

            return {
                "ip_address": f"{ip_address}",
                "status": response.status_code,
            }
        except (httpx.ConnectError, httpx.ReadTimeout):
            done.set()
            return {"ip_address": f"{ip_address}", "status": 500}
