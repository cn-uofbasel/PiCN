#!/usr/bin/env python3.6

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
            name_payload = ""
            if packet.name_payload is not None:
               name_payload = packet.name_payload
            res = "I:" + name.to_string() + ":" + name_payload
        elif(isinstance(packet, Content)):
            name_payload = ""
            if packet.name_payload is not None:
                name_payload = packet.name_payload
            content = packet.content.replace(":", "%58")
            res = "C:" + name.to_string() + ":" + name_payload + ":" + content
        elif(isinstance(packet, Nack)):
            name_payload = ""
            if packet.name_payload is not None:
                name_payload = packet.name_payload
            res = "N:" + name.to_string() + ":" + name_payload + ":" + packet.reason
        if res is not None:
            return res.encode()
        return None

    def decode(self, wire_data) -> Packet:
        data: str = wire_data.decode()
        if data[0] == "I":
            name = data.split(":")[1]
            name_payload = data.split(":")[2]
            if name_payload == "":
                name_payload = None
            return Interest(self.unescape_name(Name(name)), name_payload)
        elif data[0] == "C":
            name = data.split(":")[1]
            name_payload = data.split(":")[2]
            if name_payload == "":
                name_payload = None
            content = data.split(":")[3].replace("%58", ":")
            return Content(self.unescape_name(Name(name)), content, name_payload)
        elif data[0] == "N":
            name = data.split(":")[1]
            name_payload = data.split(":")[2]
            reason = data.split(":")[3]
            if name_payload == "":
                name_payload = None
            return Nack(self.unescape_name(Name(name)), reason, name_payload)


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
