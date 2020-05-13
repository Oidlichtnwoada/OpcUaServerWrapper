from sys import argv, exit

from IPy import IP
from opcuaserver import OpcUaServerForRobotController

MAX_PORT = 65535
MIN_PORT = 0
USAGE = f'USAGE: python {__file__} <IP_OS> <PORT_OS> <IP_RC> <PORT_RC>'
INCORRECT_IP = 'Please specify correct IP addresses!'
INCORRECT_PORT = f'Please specify ports between {MIN_PORT} and {MAX_PORT}!'


def check_port_number(port_number):
    if port_number < MIN_PORT or port_number > MAX_PORT:
        raise ValueError()


if len(argv) != 5:
    exit(USAGE)

try:
    ip_os = str(IP(argv[1]))
    ip_rc = str(IP(argv[3]))
except ValueError:
    exit(INCORRECT_IP)

try:
    port_os = int(argv[2])
    port_rc = int(argv[4])
    check_port_number(port_os)
    check_port_number(port_rc)
except ValueError:
    exit(INCORRECT_PORT)

OpcUaServerForRobotController(ip_os, port_os, ip_rc, port_rc).start()
