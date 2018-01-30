"""Internal representation of a received packet whose type is unknown"""

from .Packet import Packet
from .Name import Name


class UnknownPacket(Packet):
    """
    Internal representation of a received packet whose type is unknown
    """

    def __init__(self, name: Name = None, wire_format = None):
        assert (type(self._wire_format) in [bytes, bytearray]), "MUST be raw bytes ('None' is invalid)"
        super(UnknownPacket, self).__init__(name, wire_format)

    def __eq__(self, other):
        if type(other) is not UnknownPacket:
            return False
        return self.name == other.name