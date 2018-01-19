"""A extrem simple Packet Encoder for the BasicPacketEncodingLayer"""

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Nack, Name

class SimpleStringEncoder(BasicEncoder):
    """A extrem simple Packet Encoder for the BasicPacketEncodingLayer"""
    def __init__(self):
        BasicEncoder.__init__(self)

    def encode(self, packet: Packet):
        res = None
        name = self.escape_name(packet.name)
        if(isinstance(packet, Interest)):
            res = "I:" + name.to_string() + ":"
        elif(isinstance(packet, Content)):
            content = packet.content.replace(":", "%58")
            res = "C:" + name.to_string() + ":" + ":" + content
        elif(isinstance(packet, Nack)):
            res = "N:" + name.to_string() + ":" + ":" + packet.reason
        if res is not None:
            return res.encode()
        return None

    def decode(self, wire_data) -> Packet:
        data: str = wire_data.decode()
        if data[0] == "I":
            name = data.split(":")[1]
            return Interest(self.unescape_name(Name(name)))
        elif data[0] == "C":
            name = data.split(":")[1]
            content = data.split(":")[3].replace("%58", ":")
            return Content(self.unescape_name(Name(name)), content)
        elif data[0] == "N":
            name = data.split(":")[1]
            reason = data.split(":")[3]
            return Nack(self.unescape_name(Name(name)), reason)


    def escape_name(self, name: Name):
        """escape a name"""
        n2 = Name()
        for c in name.components:
            n2.components.append(c.replace("/", "%2F"))
        return n2

    def unescape_name(self, name: Name):
        """unescape a name"""
        n2 = Name()
        for c in name.components:
            n2.components.append(c.replace("%2F", "/"))
        return n2