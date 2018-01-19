"""NDN TLV Encoder"""

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Nack, Name

from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv

from random import SystemRandom


class NdnTlvEncoder(BasicEncoder):
    """Packet Encoder for NDN-TLV"""

    def __init__(self):
        BasicEncoder.__init__(self)

    def encode(self, packet: Packet) -> bytearray:
        """
        Python object to NDN TLV wire format
        :param packet: Packet in PiCN's representation
        :return: Packet in NDN TLV representation
        """
        if(isinstance(packet, Interest)):
            return self.encode_interest(packet.name)
        if(isinstance(packet, Content)):
            return self.encode_data(packet.name, packet.get_bytes())
        if(isinstance(packet, Nack)):
            return None # TODO
        return None

    def decode(self, wire_data) -> Packet:
        """
        NDN TLV wire format packet to python object
        :param wire_data: Packet in wire formate (NDN TLV representation)
        :return: Packet in PiCN's internal representation
        """
        # print("got %d bytes to decode" % len(wire_data))
        if(self.is_content(wire_data)):
            (name, payload) = self.decode_data(wire_data)
            return Content(name, payload)
        if(self.is_interest(wire_data)):
            name = self.decode_interest(wire_data)
            return Interest(name)
        if(self.is_nack(wire_data)):
            return None # TODO: Put into NACK Packet
        return None


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
        name = []
        while decoder.getOffset() < endOffset:
            name.append(self.decode_name_component(decoder))
        decoder.finishNestedTlvs(endOffset)
        return Name(suite='ndn2013').__add__(name)

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
        return False # TODO
