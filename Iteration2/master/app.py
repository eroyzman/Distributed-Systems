from flask import Flask, request, jsonify
import httpx
import asyncio

from settings import slaves_ip_addresses

# https://testdriven.io/blog/flask-async/
# https://anandtripathi5.medium.com/getting-started-with-async-requests-in-flask-using-httpx-8c2c5e11b831
# https://progressstory.com/tech/python/async-requests-with-flask/#implementation
# https://www.python-httpx.org/async/

app = Flask(__name__)
MESSAGES = []


@app.route('/', methods=['POST', 'GET'])
async def main():
    if request.method == 'POST':
        delay = 0
        w: str = request.json.get("write_concern")
        message: str = request.json.get("message")
        if not (request.json.get("delay") is None):
            delay = request.json.get("delay")
        MESSAGES.append(message)
        async with httpx.AsyncClient() as client:
            match w:
                case "1":
                    result = await get_multiple_addresses(message, delay)
                    return jsonify({"message": "successful"}), 200
                case "2":
                    results = await get_multiple_addresses(message, delay)
                    for result in results:
                        if result["status"] == 200:
                            return jsonify({"ip_address": result["ip_address"], "status": "successful"}), result[
                                "status"]
                    return jsonify({"message": "failed"}), 500
                case "3":
                    results = await get_multiple_addresses(message, delay)
                    for result in results:
                        if result["status"] != 200:
                            return jsonify({"ip_address": result["ip_address"], "status": "failed"}), result[
                                "status"]
                    return jsonify({"message": "successful"}), 200
                case _:
                    return jsonify({"message": "incorrect write_concern value!"})
    return ",".join(MESSAGES)


async def get_multiple_addresses(message, delay):
    async with httpx.AsyncClient() as client:
        tasks = []
        for ip_address in slaves_ip_addresses():
            task = asyncio.create_task(set_post(ip_address, client, message, delay))
            tasks.append(task)
        result = await asyncio.gather(*tasks, return_exceptions=True)
    return result


async def set_post(ip_address, client, message, delay):
    try:
        response = await client.post(ip_address, json={"message": message, "delay": delay})
        return {"ip_address": f"{ip_address}", 'status': response.status_code}
    except httpx.ConnectError:
        return {"ip_address": f"{ip_address}", 'status': 500}
