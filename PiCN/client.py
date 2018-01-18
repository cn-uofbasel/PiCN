#!/usr/bin/env python3.6
# PiCN/client.py
# (c) 2018-01-18 <christian.tschudin@unibas.ch>

import binascii
import socket
import sys
sys.path.append('..')
from random import randint,getrandbits

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Content, Interest, Nack

class ICN():

    def __init__(self):
        self.encoder = SimpleStringEncoder()
        self.sock = None

    def attach(self, ipAddr, ipPort):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_port = randint(10000, 64000)
        self.sock.bind(("0.0.0.0", send_port))
        self.ipAddr = ipAddr
        self.ipPort = ipPort
        self.prefix = "/the/prefix"
        self.repoPath = "/Users/tschudin/pap/PiCN/examples/repo"

    def detach(self):
        self.sock = None
        pass

    def getDefaultPrefix(self):
        if not self.sock:
            return None
        return self.prefix

    def writeChunk(self, name, data):
        repoDir = self.repoPath
        c = Content(name, data)
        encoded_content = self.encoder.encode(c)
        fname = binascii.hexlify(getrandbits(64).to_bytes(8, byteorder='big'))
        with open(repoDir + "/" + fname.decode('ascii'), "wb") as f:
            f.write(encoded_content)

    def readChunk(self, name):
        print("reading %s" % name)
        interest = Interest(name)
        encoded_interest = self.encoder.encode(interest)
        self.sock.sendto(encoded_interest, (self.ipAddr, self.ipPort))
        encoded_content, addr = self.sock.recvfrom(8192)
        content = self.encoder.decode(encoded_content)
        if isinstance(content, Content):
            return content.content
        return None

# eof
