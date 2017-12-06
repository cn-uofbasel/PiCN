"""Abstract Encoder for the BasicPacketEncoding Layer"""

import abc
from PiCN.Packets import Packet

class BasicEncoder(object):
    """Abstract Encoder for the BasicPacketEncoding Layer"""

    @abc.abstractclassmethod
    def encode(self, packet: Packet):
        """encode a packet to wireformat"""

    @abc.abstractclassmethod
    def decode(self, wire_data) -> Packet:
        """decode a packet to Packet data structure"""