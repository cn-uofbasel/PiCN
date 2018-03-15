"""Abstract Encoder for the BasicPacketEncoding Layer"""

import abc
from PiCN.Packets import Packet
from PiCN.Logger import Logger

class BasicEncoder(object):
    """Abstract Encoder for the BasicPacketEncoding Layer"""

    @abc.abstractmethod
    def __init__(self, log_level = 255):
        @property
        @abc.abstractmethod
        def logger(self):
            pass

    @abc.abstractmethod
    def set_log_level(self, log_level):
        pass

    @abc.abstractclassmethod
    def encode(self, packet: Packet):
        """encode a packet to wireformat"""

    @abc.abstractclassmethod
    def decode(self, wire_data) -> Packet:
        """decode a packet to Packet data structure"""