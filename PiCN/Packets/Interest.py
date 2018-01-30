"""Interest data structure for PiCN"""

from .Packet import Packet

class Interest(Packet):
    """Interest data structure for PiCN"""

    def __init__(self, name = None, wire_data = None):
        Packet.__init__(self, name)
        self._wire_data = wire_data
        assert (type(self._wire_format) in [bytes, bytearray, type(None)]), "MUST be raw bytes"

    def __eq__(self, other):
        if type(other) is not Interest:
            return False
        return self.name == other.name