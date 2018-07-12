"""Internal representation of a heartbeat"""

from PiCN.Packets import Packet

class Heartbeat(Packet):
    """
    Internal representation of an heartbeat packet
    """

    def __init__(self, name = None, wire_format = None):
        Packet.__init__(self, name, wire_format)
        assert (type(self._wire_format) in [bytes, bytearray, type(None)]), "MUST be raw bytes or None"

    def __eq__(self, other):
        if type(other) is not Heartbeat:
            return False
        return self.name == other.name