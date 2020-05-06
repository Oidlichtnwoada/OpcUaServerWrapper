from socket import socket, AF_INET, SOCK_STREAM
from sys import argv


class TelnetServer():
    def __init__(self):
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.bind((argv[1], int(argv[2])))
        self.server_socket.listen(1024)
        self.client_socket = None
        self.response = 'QoK' + '1;' * 128

    def start(self):
        while True:
            self.client_socket = self.server_socket.accept()[0]
            while True:
                request = self.client_socket.recv(1024)
                if request:
                    print(request)
                    self.client_socket.send(self.response.encode('ascii'))
                else:
                    break
            self.client_socket.close()


TelnetServer().start()
