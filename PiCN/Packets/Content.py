"""Content data structure for PiCN"""

from .Packet import Packet

class Content(Packet):
    """Content data structure for PiCN"""

    def __init__(self, name = None, content = None):
        Packet.__init__(self, name)
        self._content = content

    @property
    def content(self):
        return self._content

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