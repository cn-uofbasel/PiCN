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

    def encode(self, packet: Packet):
        return None # TODO

    def decode(self, wire_data) -> Packet:
        return None # TODO


    ### Helpers ###

    def encode_name(name: str) -> bytearray:
        """
        Assembly a name-TLV
        :param name: Name in format like /this/name/has/five/components
        :return: Name-TLV
        """
        name = name[1:].split('/')
        encoder = TlvEncoder()
        for component in name[::-1]:
            encoder.writeBlobTlv(Tlv.NameComponent, [ord(c) for c in component])
        encoder.writeTypeAndLength(Tlv.Name, len(encoder))
        return encoder.getOutput().tobytes()

    def encode_interest(name) -> bytearray:
        """
        Assembly an interest packet
        :param name: Name (as bytearray or String)
        :return: Interest-TLV
        """
        encoder = TlvEncoder()
        # Add nonce
        nonce = bytearray(4)
        for i in range(4):
            nonce[i] = SystemRandom().randint(0, 0xff)
        encoder.writeBlobTlv(Tlv.Nonce, nonce)
        # Add name
        if isinstance(name, str):
            name = encode_name(name)
        encoder.writeBuffer(name)
        # Add interest type and len
        encoder.writeTypeAndLength(Tlv.Interest, len(encoder))
        return encoder.getOutput().tobytes()

    def encode_data(name, payload: bytearray) -> bytearray:
        """
        Assembly a data packet
        :param name: Name (as bytearray or String)
        :param payload: Payload
        :return: Data-TLV
        """
        encoder = TlvEncoder()
        # Add content
        encoder.writeBuffer(payload)
        encoder.writeTypeAndLength(Tlv.Content, len(encoder))
        # Add meta info (empty)
        encoder.writeTypeAndLength(Tlv.MetaInfo, 0)
        # Add name
        if isinstance(name, str):
            name = encode_name(name)
        encoder.writeBuffer(name)
        # Add data type and len
        encoder.writeTypeAndLength(Tlv.Data, len(encoder))
        return encoder.getOutput().tobytes()


    def decode_name_component(decoder: TlvDecoder) -> bytearray:
        """
        Decode a name component
        :param decoder: Decoder
        :return: Value of name component
        """
        savePosition = decoder.getOffset()
        type = decoder.readVarNumber()
        decoder.seek(savePosition)
        return decoder.readBlobTlv(type).tobytes()

    def decode_name(decoder: TlvDecoder) -> [[bytearray]]:
        """
        Decode a name
        :param decoder: Decoder
        :return: Name (array of bytearrays)
        """
        endOffset = decoder.readNestedTlvsStart(Tlv.Name)
        name = []
        while decoder.getOffset() < endOffset:
            name.append(decode_name_component(decoder))
        decoder.finishNestedTlvs(endOffset)
        return name

    def decode_meta_info(decoder: TlvDecoder) -> None:
        """
        Decode meta info
        :param decoder: Decoder
        :return: Nothing so far
        """
        endOffset = decoder.readNestedTlvsStart(Tlv.MetaInfo)
        # Does not yet parse meta data, but:
        # Lets the decoder jump over meta data.
        decoder.finishNestedTlvs(endOffset)

    def decode_interest(input: bytearray) -> [[bytearray]]:
        """
        Decode an interest packet
        :param input: Interest packet in NDN-TLV wire format
        :return: Name (array of bytearrays)
        """
        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.Interest)
        return decode_name(decoder)

    def decode_data(input: bytearray) -> ([bytearray], bytearray):
        """
        Decodes a data packet
        :param input: Data packet in NDN-TLV wire format
        :return: Name and payload
        """
        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.Data)
        name = decode_name(decoder)
        decode_meta_info(decoder)
        payload = decoder.readBlobTlv(Tlv.Content).tobytes()
        return (name, payload)