#!/usr/bin/env python3.6

# PiCN/client.py
# (c) 2018-01-18 <christian.tschudin@unibas.ch>

import base64
import binascii
import hashlib
import os
from   random import randint
import socket
import sys
sys.path.append('..')

#from   PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from   PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from   PiCN.Layers.RepositoryLayer.Repository import SimpleFileSystemRepository
from   PiCN.Packets import Content, Interest, Name, Nack
import PiCN.Mgmt

# -----------------------------------------------------------------

class ICN():

    def __init__(self):
        # self.encoder = SimpleStringEncoder()
        self.encoder = NdnTlvEncoder.NdnTlvEncoder()
        self.sock = None

    def attach(self, ipAddr: str, ipPort: int, repoPort: int, suite: str):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_port = randint(10000, 64000)
        self.sock.bind(("0.0.0.0", send_port))
        self.ipAddr = ipAddr
        self.ipPort = ipPort
        self.suite = suite
        mgmt = PiCN.Mgmt.MgmtClient(repoPort)
        self.repoPrefix = mgmt.get_repo_prefix()
        self.repoPath = mgmt.get_repo_path()
        self.repo = SimpleFileSystemRepository(self.repoPath,
                                               self.repoPrefix)

    def detach(self):
        self.sock = None
        self.repoPrefix = None
        self.repoPath = None
        self.repo = None

    def getRepoPrefix(self) -> Name:
        return self.repoPrefix

    def getRepoPath(self) -> str:
        return self.repoPath

    def writeChunk(self, name: Name, data: bytes):
        # we bypass the mgmt interface, acccess the file system directly
        self.repo.set_content(name, data)

    def readChunk(self, name: Name, digest=None):
        interest = Interest(name)
        encoded_interest = self.encoder.encode(interest)
        self.sock.sendto(encoded_interest, (self.ipAddr, self.ipPort))
        encoded_content, addr = self.sock.recvfrom(8192)
        content = self.encoder.decode(encoded_content)
        if isinstance(content, Content):
            return content.content
        return None

# eof
