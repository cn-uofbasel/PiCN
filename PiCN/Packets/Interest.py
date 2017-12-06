"""Interest data structure for PiCN"""

from .Packet import Packet

class Interest(Packet):
    """Interest data structure for PiCN"""

    def __init__(self, name = None, name_payload = None):
        Packet.__init__(self, name, name_payload)

    def __eq__(self, other):
        if type(other) is not Interest:
            return False
        return self.name == other.name