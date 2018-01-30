"""Internal representation of a content object"""

from .Packet import Packet

class Content(Packet):
    """
    Internal representation of a content object
    """


    def __init__(self, name = None, content = None, wire_format = None):
        Packet.__init__(self, name)
        if type(content) == str:
            self._content = content.encode()
        else:
            self._content = content
        assert (type(self._content) in [bytes, bytearray, type(None)]), "MUST be raw bytes or None"
        self._wire_format = wire_format
        assert (type(self._wire_format) in [bytes, bytearray, type(None)]), "MUST be raw bytes or None"

    @property
    def content(self):
        if self._content == None:
            return None
        return self._content.decode()

    def get_bytes(self) -> bytearray:
        return self._content

    @content.setter
    def content(self, content):
        if type(content) == str:
            content = content.encode()
        assert (type(content) in [bytes, bytearray]), "MUST be raw bytes"
        self._content = content

    def __eq__(self, other):
        if type(other) is not Content:
            return False
        return self.name == other.name and self._content == other._content
