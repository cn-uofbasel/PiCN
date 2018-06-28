"""Implementation of an Interface using UDP4 for communication"""

import socket

from PiCN.Layers.LinkLayer.Interfaces import BaseInterface


class UDP4Interface(BaseInterface):
    """Implementation of an Interface using UDP4 for communication
    :param listen

    """

    def __init__(self, listen_port: int, buffersize: int=8192):
        self.listen_port = listen_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.listen_port))

        self._buffersize = buffersize

    def send(self, data, addr):
        self.sock.sendto(data, addr)

    def receive(self):
        data, addr = self.sock.recvfrom(self._buffersize)
        return data, addr

    @property
    def file_descriptor(self):
        return self.sock

    def get_port(self) -> int:
        """Returns port on which the Interface is running"""
        return int(self.sock.getsockname()[1])

    def close(self):
        self.sock.close()

    def __eq__(self, other):
        return self.get_port() == other.get_port()