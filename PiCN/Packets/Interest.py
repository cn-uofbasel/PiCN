"""Interest data structure for PiCN"""

from .Packet import Packet

class Interest(Packet):
    """Interest data structure for PiCN"""

    def __init__(self, name = None, wire_data = None):
        Packet.__init__(self, name)
        self._wire_data = wire_data

    @property
    def wire_data(self):
        return self._wire_data

    def __eq__(self, other):
        if type(other) is not Interest:
            return False
        return self.name == other.name