"""Base class for internal representation of network packets"""

from .Name import Name

class Packet(object):
    """
    Base class for internal representation of network packets
    """

    def __init__(self, name: Name = None, wire_format = None):
        if type(name) == str:
            self._name = Name(name)
        else:
            self._name: Name = name
        self._wire_format = wire_format
        assert (type(self._wire_format) in [bytes, bytearray, type(None)]), "MUST be raw bytes or None"

    def __eq__(self, other):
        if type(other) is not Packet:
            return False
        return self.name == other.name #and self.name_payload == other.name_payload

    def __hash__(self):
        return self._name.__hash__() + self._name_payload.__hash__()

    # TODO: Implement __getitem__.

    @property
    def name(self):
        """name of the packet"""
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def wire_format(self):
        return self._wire_format
