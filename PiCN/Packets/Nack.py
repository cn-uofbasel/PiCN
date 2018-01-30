"""Nack data structure for PiCN"""

from .Packet import Packet

class Nack(Packet):
    """Nack data structure for PiCN"""

    def __init__(self, name=None, wire_format=None, reason=None):
        Packet.__init__(self, name)
        self._reason = reason
        self._wire_format = wire_format
        assert (type(self._wire_format) in [bytes, bytearray, type(None)]), "MUST be raw bytes"

    @property
    def reason(self):
        return self._reason

    @reason.setter
    def reason(self, reason):
        self._reason = reason

    def __eq__(self, other):
        if type(other) is not Nack:
            return False
        return self.name == other.name and self.reason == other.reason