"""NDN TLV Encoder"""

from PiCN.Logger import Logger
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Nack, NackReason, Name, UnknownPacket

from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv

from random import SystemRandom


class NdnTlvEncoder(BasicEncoder):
    """
    Packet Encoder for NDN-TLV

        Implemented Specifications:

       - NDN Packet Format Specification 0.2-2 documentation (partially)
         http://named-data.net/doc/NDN-TLV/current/intro.html (February 2018)

       - NDNLPv2 / link protocol (partially)
         https://redmine.named-data.net/projects/nfd/wiki/NDNLPv2 (February 2018)

       - Additional in-network computation related NACK Reasons

    """

    __nack_reason_values = {
        NackReason.CONGESTION: 50,                  # NDNLPv2 compatible
        NackReason.DUPLICATE: 100,                  # NDNLPv2 compatible
        NackReason.NO_ROUTE: 150,                   # NDNLPv2 compatible
        NackReason.NO_CONTENT: 160,                 # extension: does not exist in NDNLPv2
        NackReason.COMP_QUEUE_FULL: 161,            # extension: does not exist in NDNLPv2
        NackReason.COMP_PARAM_UNAVAILABLE: 162,     # extension: does not exist in NDNLPv2
        NackReason.COMP_EXCEPTION: 163,             # extension: does not exist in NDNLPv2
        NackReason.COMP_TERMINATED: 164             # extension: does not exist in NDNLPv2
    }
    """Mapping of NackReason Enum to wire format values"""

    __nack_reason_enum = {
         50: NackReason.CONGESTION,                 # NDNLPv2 compatible
        100: NackReason.DUPLICATE,                  # NDNLPv2 compatible
        150: NackReason.NO_ROUTE,                   # NDNLPv2 compatible
        160: NackReason.NO_CONTENT,                 # extension: does not exist in NDNLPv2
        161: NackReason.COMP_QUEUE_FULL,            # extension: does not exist in NDNLPv2
        162: NackReason.COMP_PARAM_UNAVAILABLE,     # extension: does not exist in NDNLPv2
        163: NackReason.COMP_EXCEPTION,             # extension: does not exist in NDNLPv2
        164: NackReason.COMP_TERMINATED             # extension: does not exist in NDNLPv2
    }
    """Mapping of wire format nack reasons to NackReason Enum"""

    def __init__(self, debug_level = 255):
        BasicEncoder.__init__(self)
        self.logger = Logger("NdnTlvEnc", debug_level)

    def encode(self, packet: Packet) -> bytearray:
        """
        Python object (PiCN's internal representation) to NDN TLV wire format
        :param packet: Packet in PiCN's representation
        :return: Packet in NDN TLV representation
        """
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
        if isinstance(packet, UnknownPacket):
            self.logger.info("Encode UnknownPacket")
            return packet.wire_format

    def decode(self, wire_data) -> Packet:
        """
        NDN TLV wire format packet to python object (PiCN's internal representation)
        :param wire_data: Packet in wire format (NDN TLV representation)
        :return: Packet in PiCN's internal representation
        """
        # print("got %d bytes to decode" % len(wire_data))
        if(self.is_content(wire_data)):
            self.logger.info("Decode content object")
            (name, payload) = self.decode_data(wire_data)
            return Content(name, payload, wire_data)
        if(self.is_interest(wire_data)):
            self.logger.info("Decode interest")
            name = self.decode_interest(wire_data)
            return Interest(name, wire_data)
        if(self.is_nack(wire_data)):
            self.logger.info("Decode NACK")
            (name, reason) = self.decode_nack(wire_data)
            return Nack(name, reason, wire_format=wire_data)
        else:
            self.logger.info("Decode failed (unknown packet type)")
            return UnknownPacket(wire_format=wire_data)


    ### Helpers ###

    def encode_name(self, name: Name) -> bytearray:
        """
        Assembly a name-TLV
        :param name: Name
        :return: Name-TLV
        """
        encoder = TlvEncoder()
        # name = name[1:].split('/')
        # for component in name[::-1]:
        #     encoder.writeBlobTlv(Tlv.NameComponent, [ord(c) for c in component])
        # fill backwards
        if name.digest:
            encoder.writeBlobTlv(Tlv.ImplicitSha256DigestComponent, name.digest)
        for c in name._components[::-1]:
            encoder.writeBlobTlv(Tlv.NameComponent, c)
        encoder.writeTypeAndLength(Tlv.Name, len(encoder))
        return encoder.getOutput() #.tobytes()

    def encode_interest(self, name: Name) -> bytearray:
        """
        Assembly an interest packet
        :param name: Name
        :return: Interest-TLV
        """
        encoder = TlvEncoder()
        # Add nonce
        nonce = bytearray(4)
        for i in range(4):
            nonce[i] = SystemRandom().randint(0, 0xff)
        encoder.writeBlobTlv(Tlv.Nonce, nonce)
        # TODO: add implicitDigest flag here ?
        # Add name
        encoder.writeBuffer(self.encode_name(name))
        # Add interest type and len
        encoder.writeTypeAndLength(Tlv.Interest, len(encoder))
        return encoder.getOutput().tobytes()

    def encode_data(self, name: Name, payload: bytearray) -> bytearray:
        """
        Assembly a data packet
        :param name: Name
        :param payload: Payload
        :return: Data-TLV
        """
        encoder = TlvEncoder()
        # Add content
        encoder.writeBlobTlv(Tlv.Content, payload)
        # Add meta info (empty)
        encoder.writeTypeAndLength(Tlv.MetaInfo, 0)
        # Add name
        encoder.writeBuffer(self.encode_name(name))
        # Add data type and len
        encoder.writeTypeAndLength(Tlv.Data, len(encoder))
        return encoder.getOutput().tobytes()

    def encode_nack(self, name: Name, reason: NackReason, interest: Interest) -> bytearray:
        """
        Assembly a negative acknowledgement packet
        :param name: Name carried by interest for which this NACK is generated
        :param reason: Nack reason
        :param interest: Interest for which this NACk is generated
        :return:  NACK-TLV
        """
        encoder = TlvEncoder()
        # write fragment (interest packet)
#        if interest.wire_format is None:
#            interest_encoder = NdnTlvEncoder()
#            interest_encoder.encode_interest(interest)
#            interest.wire_format = interest_encoder.getOutput().tobytes()
        encoder.writeBuffer(interest.wire_format)
        encoder.writeTypeAndLength(Tlv.LpPacket_Fragment, len(encoder))
        fragment_len = len(encoder)
        # write nack reason if needed
        if reason is not NackReason.NOT_SET:
            wire_reason = self.encode_nack_reason(reason)
            encoder.writeBuffer(wire_reason)
            encoder.writeTypeAndLength(Tlv.LpPacket_NackReason, len(wire_reason))
        # write nack header
        encoder.writeTypeAndLength(Tlv.LpPacket_Nack, len(encoder) - fragment_len)
        # write link packet header
        encoder.writeTypeAndLength(Tlv.LpPacket_LpPacket, len(encoder))
        return encoder.getOutput().tobytes()

    def encode_nack_reason(self, reason: NackReason) -> bytearray:
        """
        Encode a NackReason
        :param reason: NackReason
        :return: Nack reason in wire format
        """
        encoder = TlvEncoder()
        encoder.writeVarNumber(self.__nack_reason_values[reason])
        return encoder.getOutput().tobytes()

    def decode_name_component(self, decoder: TlvDecoder) -> bytearray:
        """
        Decode a name component
        :param decoder: Decoder
        :return: Value of name component
        """
        savePosition = decoder.getOffset()
        type = decoder.readVarNumber()
        decoder.seek(savePosition)
        return decoder.readBlobTlv(type).tobytes()

    def decode_name(self, decoder: TlvDecoder) -> Name:
        """
        Decode a name
        :param decoder: Decoder
        :return: Name
        """
        endOffset = decoder.readNestedTlvsStart(Tlv.Name)
        comps = []
        dgest = None
        while decoder.getOffset() < endOffset:
            if decoder.peekType(Tlv.ImplicitSha256DigestComponent, endOffset):
                dgest = decoder.readBlobTlv(Tlv.ImplicitSha256DigestComponent)
                dgest = dgest.tobytes()
            else:
                comps.append(self.decode_name_component(decoder))
        decoder.finishNestedTlvs(endOffset)
        return Name(suite='ndn2013').__add__(comps).setDigest(dgest)

    def decode_meta_info(self, decoder: TlvDecoder) -> None:
        """
        Decode meta info
        :param decoder: Decoder
        :return: Nothing so far
        """
        endOffset = decoder.readNestedTlvsStart(Tlv.MetaInfo)
        # Does not yet parse meta data, but:
        # Lets the decoder jump over meta data.
        decoder.finishNestedTlvs(endOffset)

    def decode_interest(self, input: bytearray) -> Name:
        """
        Decode an interest packet
        :param input: Interest packet in NDN-TLV wire format
        :return: Name
        """
        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.Interest)
        return self.decode_name(decoder)

    def decode_data(self, input: bytearray) -> ([bytearray], bytearray):
        """
        Decodes a data packet
        :param input: Data packet in NDN-TLV wire format
        :return: Name and payload
        """
        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.Data)
        name = self.decode_name(decoder)
        self.decode_meta_info(decoder)
        payload = decoder.readBlobTlv(Tlv.Content).tobytes()
        return (name, payload)

    def decode_nack(self, input: bytearray) -> (Name, NackReason):
        """
        Decode NACK packet
        :param input: Data packet in NDN-TLV wire format
        :return: Name
        """
        # decode name
        name = self.decode_interest(input[13:])
        # decode nack reason
        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.LpPacket_LpPacket)
        decoder.readNestedTlvsStart(Tlv.LpPacket_Nack)
        try:
            decoder.readNestedTlvsStart(Tlv.LpPacket_NackReason)
            wire_reason = decoder.readVarNumber()
            reason = self.__nack_reason_enum(wire_reason)
        except ValueError:
            # happens when nack reason is not specified
            reason = NackReason.NOT_SET
        return (name, reason)

    def is_content(self, input: bytearray) -> bool:
        """
        Checks if content object packet
        :param input:  Packet in NDN-TLV wire format
        :return: True if content object
        """
        return input[0] == Tlv.Data

    def is_interest(self, input: bytearray) -> bool:
        """
        Checks if interest packet
        :param input:  Packet in NDN-TLV wire format
        :return: True if interest
        """
        return input[0] == Tlv.Interest

    def is_nack(selfself, input: bytearray) -> bool:
        """
        Checks if NACK packet
        :param input:  Packet in NDN-TLV wire format
        :return: True if NACK
        """
        return input[0] == 0x64 and input[3] == 0x03  and input[4] == 0x20
