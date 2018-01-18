#!/usr/bin/env python3.6

"""Client for The Mgmt of PiCN"""

import socket

from PiCN.Packets import Name

class MgmtClient(object):
    """Client for The Mgmt of PiCN"""

    def __init__(self, port = 9000):
        self.target_port = port
        self.target_ip = "127.0.0.1"

    def add_face(self, ip_addr: str, port: int):
        """add a new face"""
        param = ip_addr + ":" + str(port)
        return self.layercommand("linklayer", "newface", param)

    def add_forwarding_rule(self, name: Name, faceid: int):
        param = name.to_string() + ":" + str(faceid)
        return self.layercommand("icnlayer", "newforwardingrule", param.replace("/", "%2F"))

    def add_new_content(self, name: Name, data):
        param = name.to_string() + ":" + data
        return self.layercommand("icnlayer", "newcontent", param.replace("/", "%2F"))

    def get_repo_prefix(self):
        reply = self.layercommand("repolayer", "getprefix", "")
        return self.parseHTTPReply(reply)

    def get_repo_path(self):
        reply = self.layercommand("repolayer", "getpath", "")
        return self.parseHTTPReply(reply)

    def parseHTTPReply(self, data: str):
        data = data.replace("HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n ", "")
        data = data[:-5]
        return data

    def layercommand(self, layer: str, command: str, param: str) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.target_ip, self.target_port))
        sock.send(("GET /" + str(layer) + "/" + str(command) + "/" + str(param) + " HTTP/1.1\r\n\r\n").encode())
        data = sock.recv(1024)
        sock.close()
        return data.decode()

    def shutdown(self) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.target_ip, self.target_port))
        sock.send("GET /shutdown HTTP/1.1\r\n\r\n".encode())
        data = sock.recv(1024)
        sock.close()
        return data.decode()
