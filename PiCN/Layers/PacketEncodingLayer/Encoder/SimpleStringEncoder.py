"""A extrem simple Packet Encoder for the BasicPacketEncodingLayer"""

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Name, Nack, NackReason, UnknownPacket

class SimpleStringEncoder(BasicEncoder):
    """An extreme simple Packet Encoder for the BasicPacketEncodingLayer"""
    def __init__(self, log_level=255):
        BasicEncoder.__init__(self, logger_name="SimpleEnc", log_level=log_level)

    def encode(self, packet: Packet):
        res = None
        name = self.escape_name(packet.name)
        if(isinstance(packet, Interest)):
            self.logger.info("Encode interest")
            res = "I:" + name.to_string() + ":"
        elif(isinstance(packet, Content)):
            self.logger.info("Encode content object")
            content = packet.content
            content = content.replace(":", "%58")
            res = "C:" + name.to_string() + ":" + ":" + content
        elif(isinstance(packet, Nack)):
            self.logger.info("Encode NACK")
            res = "N:" + name.to_string() + ":" + ":" + packet.reason.value
        elif(isinstance(packet, UnknownPacket)):
            res = packet.wire_format
        if res is not None:
            return res.encode()
        return None

    def decode(self, wire_data) -> Packet:
        data: str = wire_data.decode()
        if data[0] == "I":
            self.logger.info("Decode interest")
            name = data.split(":")[1]
            return Interest(self.unescape_name(Name(name)))
        elif data[0] == "C":
            self.logger.info("Decode content object")
            name = data.split(":")[1]
            content = data.split(":")[3].replace("%58", ":")
            return Content(self.unescape_name(Name(name)), content)
        elif data[0] == "N":
            self.logger.info("Decode NACK")
            name = data.split(":")[1]
            reason = NackReason(data.split(":")[3])
            return Nack(self.unescape_name(Name(name)), reason, None)
        else:
            self.logger.info("Decode failed (unknown packet type)")
            return UnknownPacket(wire_format=wire_data)


    def escape_name(self, name: Name):
        """escape a name"""
        n2 = Name()
        for c in name.string_components:
            n2 += c.replace("/", "%2F")
        return n2

    def unescape_name(self, name: Name):
        """unescape a name"""
        n2 = Name()
        for c in name.string_components:
            n2 += c.replace("%2F", "/")
        return n2
