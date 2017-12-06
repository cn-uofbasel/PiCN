"""Packet data structure for PiCN"""

from ..Packets.Name import Name

class Packet(object):
    """Packet data structure for PiCN"""

    def __init__(self, name: Name=None, name_payload=None):
        if type(name) == str:
            self._name = Name(name)
        else:
            self._name: Name = name
        self._name_payload = name_payload

    def __eq__(self, other):
        if type(other) is not Packet:
            return False
        return self.name == other.name #and self.name_payload == other.name_payload

    def __hash__(self):
        return self._name.__hash__() + self._name_payload.__hash__()

    @property
    def name(self):
        """name of the packet"""
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def name_payload(self):
        return self._name_payload

    @name_payload.setter
    def name_payload(self, name_payload):
        self._name_payload = name_payload

