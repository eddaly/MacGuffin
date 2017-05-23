#!/usr/bin/python

import socket
import sys

UDP_IP = "0.0.0.0"
UDP_PORT = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print "Server started on " + UDP_IP + ":" + str(UDP_PORT)
while True:
    payload, addr = sock.recvfrom(1024)
    print "Received: " + payload
sock.close()
