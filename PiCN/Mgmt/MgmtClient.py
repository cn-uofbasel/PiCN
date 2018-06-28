"""Client for The Mgmt of PiCN"""

import socket

from PiCN.Packets import Name

class MgmtClient(object):
    """Client for The Mgmt of PiCN"""

    def __init__(self, port = 9000):
        self.target_port = port
        self.target_ip = "127.0.0.1"

    def add_face(self, ip_addr: str, port: int, if_num: int) -> str:
        """add a new face
        :param ip_addr: id address on which the face points to
        :param port: port the face points to
        :param if_num: identify of the interface the face is using
        :return: reply message of the relay
        """
        param = ip_addr + ":" + str(port) + ":" + str(if_num)
        return self.layercommand("linklayer", "newface", param)

    def add_upd_device(self, port) -> str:
        """creates a new device using a udp socket
        :param port: the port on which the device is listening
        :return: reply message of the relay
        """
        param = str(port)
        return self.layercommand("linklayer", "newUDPdevice", param)

    def add_forwarding_rule(self, name: Name, faceid: int) -> str:
        """adding a new forwarding rule to a face
        :param name: name for the forwarding rule which should be bound to the face
        :param faceid: face id to identify the face on which the name should be bound
        :return: reply message of the relay
        """
        param = name.to_string() + ":" + str(faceid)
        return self.layercommand("icnlayer", "newforwardingrule", param.replace("/", "%2F"))

    def add_new_content(self, name: Name, data) -> str:
        """adding new content to the content store of a relay
        :param name: name of the content
        :param data: data of the content
        :return: reply message of the relay
        """
        param = name.to_string() + ":" + data
        return self.layercommand("icnlayer", "newcontent", param.replace("/", "%2F"))

    def get_repo_prefix(self) -> str:
        """get the prefix that is used by a repo
        :return reply message of the relay, containing the prefix
        """
        reply = self.layercommand("repolayer", "getprefix", "")
        reply = self.parseHTTPReply(reply)
        return Name(reply)

    def get_repo_path(self) -> str:
        """get the file system path that is used by a repo
        :return reply message of the relay, containing the file system path
        """
        reply = self.layercommand("repolayer", "getpath", "")
        return self.parseHTTPReply(reply)

    def parseHTTPReply(self, data: str) -> str:
        """parses a reply messages and removes the http tags
        :param data: reply message
        :return: reply message without http tags
        """
        data = data.replace("HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n ", "")
        data = data[:-5]
        return data

    def layercommand(self, layer: str, command: str, param: str) -> str:
        """executes a mgmt command. creates a mgmt message, send it to a relay and receives the reply msg
        :param layer: name of the layer the command targets
        :param command: mgmt command that should be executed
        :param param: parameter(s) for the command, should all be wrapped into a single string
         :return: reply message of the relay
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.target_ip, self.target_port))
        sock.send(("GET /" + str(layer) + "/" + str(command) + "/" + str(param) + " HTTP/1.1\r\n\r\n").encode())
        data = sock.recv(1024)
        sock.close()
        return data.decode()

    def shutdown(self) -> str:
        """shutdown a relay
        :return: reply message of the relay
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.target_ip, self.target_port))
        sock.send("GET /shutdown HTTP/1.1\r\n\r\n".encode())
        data = sock.recv(1024)
        sock.close()
        return data.decode()
