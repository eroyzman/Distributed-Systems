import socket
import threading
import time
import json

# HOST = '127.0.0.1'
HOST = socket.gethostbyname('master_dns')
PORT = 9090


class Client:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()

    def write(self, message):
        self.sock.send(json.dumps(jsonMessage).encode('utf-8'))

    def stop(self):
        self.sock.close()

    def receive(self):
        while True:
            try:
                message = self.sock.recv(1024).decode('utf-8')
                print(message)
            except ConnectionAbortedError:
                break
            except:
                print("Error")
                self.socket.close()


client = Client(HOST, PORT)
while 1:
    time.sleep(1)
    msg = input('>>Enter command (POST, GET only yet)\n>>').lower().strip()
    if not (msg == 'post' or msg == 'get'):
        print('Unknown command')
    else:
        command = msg.upper()
        payload = input('>>Enter message\n>>')
        jsonMessage = {"command": command, "payload": payload}
        client.write(jsonMessage)

