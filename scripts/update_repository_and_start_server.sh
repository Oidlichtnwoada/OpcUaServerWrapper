#!/bin/bash

cd /home/pi/OpcUaServerWrapper/src
/usr/bin/git pull
/usr/local/bin/python3.8 /home/pi/OpcUaServerWrapper/src/startserver.py 192.168.162.84 4840 192.168.162.82 10003
