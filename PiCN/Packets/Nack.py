"""Nack data structure for PiCN"""

from .Packet import Packet

class Nack(Packet):
    """Nack data structure for PiCN"""

    def __init__(self, name = None, reason = None, name_payload = None):
        Packet.__init__(self, name, name_payload)
        self._reason = reason

    @property
    def reason(self):
        return self._reason

    @reason.setter
    def reason(self, reason):
        self._reason = reason

    def __eq__(self, other):
        if type(other) is not Nack:
            return False
        return self.name == other.name and self.name_payload == other.name_payload and self.reason == other.reason