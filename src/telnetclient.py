from telnetlib import Telnet
from threading import Thread, Lock
from time import sleep


class TelnetClient:
    def __init__(self, ip, port, timeout, setup_method, test_command, encoding):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.setup_method = setup_method
        self.test_command = test_command
        self.encoding = encoding
        self.client_lock = Lock()
        self.client = None
        self.connect_to_server()
        ConnectionMaintainer(self).start()

    def connect_to_server(self):
        while True:
            try:
                with self.client_lock:
                    self.client = Telnet(self.ip, self.port, self.timeout)
                break
            except OSError:
                sleep(1)

    def send_request_and_return_response(self, req, timeout_factor=1):
        try:
            with self.client_lock:
                self.client.read_very_eager()
                self.client.write(req.encode(self.encoding))
                sleep(self.timeout * timeout_factor)
                return self.client.read_very_eager().decode(self.encoding)
        except EOFError:
            return ''


class ConnectionMaintainer(Thread):
    def __init__(self, telnet_client):
        Thread.__init__(self)
        self.telnet_client = telnet_client

    def run(self):
        while True:
            if self.telnet_client.send_request_and_return_response(self.telnet_client.test_command) == '':
                self.telnet_client.connect_to_server()
                self.telnet_client.setup_method()
            sleep(10)
