import socket
import threading
import json

# HOST = '127.0.0.1'
HOST = socket.gethostbyname('master_dns_name')
PORT = 9090
messageList = []


class Client:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()

    def write(self, message):
        message = message.encode('utf-8')
        self.sock.send(message)

    def stop(self):
        self.sock.close()

    def receive(self):
        while True:
            try:
                sockRecv = self.sock.recv(1024).decode('utf-8')
                jsonLoads = json.loads(sockRecv)
                match (jsonLoads["command"]):
                    case "GET":
                        getMessageList = self.do_GET()
                        print(f"Master asked GET {getMessageList}")
                    case "POST":
                        messageList.append(jsonLoads["payload"])
                        jsonMessage = {"command": "ACK", "payload": "success"}
                        self.sock.send(json.dumps(jsonMessage).encode('utf-8'))
                        print(jsonLoads["payload"])
                    case "INFO":
                        print(jsonLoads["payload"])
                    case _:
                        pass

            except ConnectionAbortedError:
                break
            except:
                print("Error")
                self.socket.close()

    def do_GET(self):
        if messageList:
            return messageList

    def do_json(command, message):
        jsonMessage = {"command": command, "payload": message}
        data = json.dumps(jsonMessage).encode('utf-8')
        return data


client = Client(HOST, PORT)
