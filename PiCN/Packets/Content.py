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
        if content == None:
            self.content = b""

    # This shoudn't be necessary: content() should work
    def get_content(self):
        try:
            return self._content.decode()
        except:
            return "".join(" 0x%02x" % x for x in self._content)[1:]

    @property
    def content(self) -> str:
        if self._content == None:
            print("Check.")
            return None
        try:
            return self._content.decode()
        except:
            return "".join(" 0x%02x" % x for x in self._content)[1:]

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
