"""Internal representation of an NACK (negative acknowledgement) packet"""

from .Packet import Packet
from .Interest import Interest

class Nack(Packet):
    """
    Internal representation of an NACK (negative acknowledgement) packet
    """

    def __init__(self, name=None, wire_format=None, reason=None, interest=None):
        Packet.__init__(self, name)
        self._reason = reason
        self._wire_format = wire_format
        self._interest = interest
        assert (type(self._wire_format) in [bytes, bytearray, type(None)]), "MUST be raw bytes or None"
        assert (type(self._interest) in [Interest, type(None)]), "MUST be Interest or None"

    @property
    def reason(self):
        return self._reason

    @property
    def interest(selfs):
        return selfs._interest

    @reason.setter
    def reason(self, reason):
        self._reason = reason

    @interest.setter
    def interest(self, i:Interest):
        self._interest = i

    def __eq__(self, other):
        if type(other) is not Nack:
            return False
        return self.name == other.name and self.reason == other.reason