"""NDN TLV Encoder (Extended)"""

from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Packets import Packet, Content, Interest, Name, Nack, UnknownPacket
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCN.Playground.Heartbeats.Layers.PacketEncoding.Heartbeat import Heartbeat


class ExtendedNdnTlvEncoder(NdnTlvEncoder):


    def __init__(self, log_level=255):
        NdnTlvEncoder.__init__(self, log_level=log_level)
        self.heartbeatTV = 0x02 # deliberately picked for this prototype :)

    def encode(self, packet: Packet) -> bytearray:
        if isinstance(packet, Interest):
            self.logger.info("Encode interest")
            if isinstance(packet.wire_format, bytes):
                return packet.wire_format
            else:
                return self.encode_interest(packet.name)
        if isinstance(packet, Content):
            self.logger.info("Encode content object")
            if isinstance(packet.wire_format, bytes):
                return packet.wire_format
            else:
                return self.encode_data(packet.name, packet.get_bytes())
        if isinstance(packet, Nack):
            self.logger.info("Encode NACK")
            if isinstance(packet.wire_format, bytes):
                return packet.wire_format
            else:
                return self.encode_nack(packet.name, packet.reason, packet.interest)
        if isinstance(packet, Heartbeat):
            self.logger.info("Encode Heartbeat")
            if isinstance(packet.wire_format, bytes):
                return packet.wire_format
            else:
                return self.encode_heartbeat(packet.name)
        if isinstance(packet, UnknownPacket):
            self.logger.info("Encode UnknownPacket")
            return packet.wire_format

    def decode(self, wire_data) -> Packet:
        # print("got %d bytes to decode" % len(wire_data))
        if(self.is_content(wire_data)):
            self.logger.info("Decode content object")
            try:
                (name, payload) = self.decode_data(wire_data)
                return Content(name, payload, wire_data)
            except:
                self.logger.info("Decoding failed (malformed packet)")
                return UnknownPacket(wire_format=wire_data)
        if(self.is_interest(wire_data)):
            self.logger.info("Decode interest")
            try:
                name = self.decode_interest(wire_data)
                return Interest(name, wire_data)
            except:
                self.logger.info("Decoding failed (malformed packet)")
                return UnknownPacket(wire_format=wire_data)
        if(self.is_heartbeat(wire_data)):
            self.logger.info("Decode heartbeat")
            try:
                name = self.decode_heartbeat(wire_data)
                return Heartbeat(name, wire_data)
            except:
                self.logger.info("Decoding failed (malformed packet)")
                return UnknownPacket(wire_format=wire_data)
        if(self.is_nack(wire_data)):
            self.logger.info("Decode NACK")
            try:
                (name, reason) = self.decode_nack(wire_data)
                return Nack(name, reason, None, wire_format=wire_data)
            except:
                self.logger.info("Decoding failed (malformed packet)")
                return UnknownPacket(wire_format=wire_data)
        else:
            self.logger.info("Decode failed (unknown packet type)")
            return UnknownPacket(wire_format=wire_data)


    def decode_heartbeat(self, input: bytearray) -> Name:
        """
        Decode a heartbeat packet
        :param input: Heartbeat packet in NDN-TLV wire format
        :return: Name
        """
        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(self.heartbeatTV)
        return self.decode_name(decoder)

    def encode_heartbeat(self, name: Name) -> bytearray:
        """
        Assembly an heartbeat packet
        :param name: Name
        :return: Heartbeat-TLV
        """
        encoder = TlvEncoder()
        # Add name
        encoder.writeBuffer(self.encode_name(name))
        # Add heartbeat type and len
        encoder.writeTypeAndLength(self.heartbeatTV, len(encoder))
        return encoder.getOutput().tobytes()

    def is_heartbeat(self, input: bytearray) -> bool:
        """
        Checks if heartbeat packet
        :param input:  Packet in NDN-TLV wire format
        :return: True if heartbeat
        """
        try:
            return input[0] == self.heartbeatTV
        except:
            return False