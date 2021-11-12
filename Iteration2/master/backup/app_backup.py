from flask import Flask, request, jsonify
import httpx

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
        ip_cnt = 0
        json_msg = {}
        send_message = ''
        w: str = request.json.get("write_concern")
        message: str = request.json.get("message")
        if not (request.json.get("delay") is None):
            delay = request.json.get("delay")
        MESSAGES.append(message)
        async with httpx.AsyncClient() as client:
            match w:
                case "1":
                    for ip_address in slaves_ip_addresses():
                        try:
                            # await client.post(ip_address, json={"message": message, "delay": delay})
                            httpx.post(ip_address, json={"message": message, "delay": delay})
                        except httpx.ConnectError:
                            pass
                    return jsonify({"message": "successful"}), 200
                case "2":
                    for ip_address in slaves_ip_addresses():
                        try:
                            # response = await client.post(ip_address, json={"message": message, "delay": delay})
                            response = httpx.post(ip_address, json={"message": message, "delay": delay})
                            json_msg[f"ip_address_{ip_cnt}"] = await do_message(ip_address, response)
                            if response.status_code == 200:
                                return jsonify(json_msg), response.status_code
                        except httpx.ConnectError:
                            json_msg[f"ip_address_{ip_cnt}"] = await do_message(ip_address, None)
                        ip_cnt += 1
                    return jsonify(json_msg), 404
                case "3":
                    for ip_address in slaves_ip_addresses():
                        try:
                            # response = await client.post(ip_address, json={'message': message, "delay": delay})
                            response = httpx.post(ip_address, json={'message': message, "delay": delay})
                            json_msg[f"ip_address_{ip_cnt}"] = await do_message(ip_address, response)
                            if response.status_code != 200:
                                return jsonify(json_msg), response.status_code
                        except httpx.ConnectError:
                            json_msg[f"ip_address_{ip_cnt}"] = await do_message(ip_address, None)
                            return jsonify(json_msg), 404
                        ip_cnt += 1
                    return jsonify(json_msg), response.status_code
                case _:
                    return jsonify({"message": "incorrect write concern value!"})
    return ",".join(MESSAGES)


async def do_message(ip_address, response):
    status = "successful"
    if (response is None) or (response.status_code != 200):
        status = "failed"
    sub_json_msg = {"status": status, "address": f"{ip_address}"}
    return sub_json_msg
