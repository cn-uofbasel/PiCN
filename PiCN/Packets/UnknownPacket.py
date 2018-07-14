"""Internal representation of a received packet whose type is unknown"""

from .Packet import Packet


class UnknownPacket(Packet):
    """
    Internal representation of a received packet whose type is unknown
    """

    def __init__(self, name=None, wire_format=None):
        Packet.__init__(self, name=None, wire_format=wire_format)
        assert (type(self.wire_format) in [bytes, bytearray]), "MUST be raw bytes ('None' is invalid)"

    def __eq__(self, other):
        if type(other) is not UnknownPacket:
            return False
        return self.name == other.name
