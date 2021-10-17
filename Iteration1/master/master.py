import socket
import threading
import json

# HOST = '127.0.0.1'
# HOST = '0.0.0.0'
HOST = socket.gethostbyname('master_dns')
PORT = 9090

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))

server.listen()

clients = []
messageList = []


def broadcast(command, message):
    data = do_json(command, message)
    for client in clients:
        client.send(data)


def do_json(command, message):
    jsonMessage = {"command": command, "payload": message}
    data = json.dumps(jsonMessage).encode('utf-8')
    return data


def handle(client, address):
    while True:
        try:
            clientRecv = client.recv(1024).decode('utf-8')
            jsonLoads = json.loads(clientRecv)
            match (jsonLoads["command"]):
                case "POST":
                    message = do_POST(jsonLoads["payload"])
                    print(f"Client {str(address)} asked POST {message}")
                    broadcast("POST", message)
                case "GET":
                    getMessageList = do_GET()
                    print(f"Client {str(address)} asked GET {getMessageList}")
                case "ACK":
                    print(f"Client {str(address)} acknowledged POST {jsonLoads['payload']}")
                case _:
                    pass
        except:
            clients.remove(client)
            print(f"Client {address} disconnected")
            client.close()
            pass


def do_GET():
    if messageList:
        return messageList


def do_POST(message):
    messageList.append(message)
    return message


def receive():
    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}!")
        clients.append(client)
        client.send(do_json("INFO", "Connected to the server"))
        thread = threading.Thread(target=handle, args=(client, address))
        thread.start()


print("Server running...")

receive()

# to do
# write GET
# JSON parese
# Docker
