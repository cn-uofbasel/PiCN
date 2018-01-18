#!/usr/bin/env python3.6

# PiCN/client.py
# (c) 2018-01-18 <christian.tschudin@unibas.ch>

import os
from   random import randint
import socket
import sys
sys.path.append('..')

from   PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from   PiCN.Packets import Content, Interest, Nack
import PiCN.Mgmt

# -----------------------------------------------------------------

class ICN():

    def __init__(self):
        self.encoder = SimpleStringEncoder()
        self.sock = None

    def attach(self, ipAddr: str, ipPort: int, repoPort: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_port = randint(10000, 64000)
        self.sock.bind(("0.0.0.0", send_port))
        self.ipAddr = ipAddr
        self.ipPort = ipPort
        mgmt = PiCN.Mgmt.MgmtClient(repoPort)
        self.repoPrefix = mgmt.get_repo_prefix()
        self.repoPath = mgmt.get_repo_path()

    def detach(self):
        self.sock = None

    def getRepoPrefix(self):
        if not self.sock:
            return None
        return self.repoPrefix

    def getRepoPath(self):
        if not self.sock:
            return None
        return self.repoPath

    def writeChunk(self, name: str, data: bytes):
        pfx = self.repoPrefix + '/'
        if name[:len(pfx)] != pfx:
            print("wrong prefix")
            return
        fname = os.path.join(self.repoPath, name[len(pfx):])
        # FIXME: should create subdirectories if fname has slashes
        if os.path.isfile(fname):
            raise IOError
        with open(fname, "wb") as f:
            f.write(data)

    def readChunk(self, name: str):
        interest = Interest(name)
        encoded_interest = self.encoder.encode(interest)
        self.sock.sendto(encoded_interest, (self.ipAddr, self.ipPort))
        encoded_content, addr = self.sock.recvfrom(8192)
        content = self.encoder.decode(encoded_content)
        if isinstance(content, Content):
            return content.content
        return None

# eof
