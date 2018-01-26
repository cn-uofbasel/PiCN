"""Content data structure for PiCN"""

from .Packet import Packet

class Content(Packet):
    """Content data structure for PiCN"""

    def __init__(self, name = None, content = None, wire_data = None):
        Packet.__init__(self, name)
        self._content = content
        self._wire_data = wire_data

    @property
    def content(self):
        if self._content == None:
            return None
        if type(self._content) is str:
            return self._content
        else:
            return self._content.decode('ascii')

    @property
    def wire_data(self):
        return self._wire_data

    def get_bytes(self) -> bytearray:
        if(isinstance(self._content, bytearray)):
            return self._content
        if(isinstance(self._content, bytes)):
            return self._content
        if(isinstance(self._content, str)):
            return self._content.encode()
        else:
            return self._content

    @content.setter
    def content(self, content):
        self._content = content

    def __eq__(self, other):
        if type(other) is not Content:
            return False
        return self.name == other.name and self.content == other.content