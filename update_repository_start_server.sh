#!/bin/bash

/usr/bin/git pull
/usr/bin/python3.7 /home/pi/OpcUaServerWrapper/telnetserver.py 127.0.0.1 23 &
cd /home/pi/OpcUaServerWrapper
/usr/bin/python3.7 /home/pi/OpcUaServerWrapper/startserver.py 192.168.162.84 4840 127.0.0.1 23
