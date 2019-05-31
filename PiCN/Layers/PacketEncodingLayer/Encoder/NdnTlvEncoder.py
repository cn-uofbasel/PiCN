"""NDN TLV Encoder"""

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Nack, NackReason, Name, UnknownPacket, Signature, SignatureType

from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv

from random import SystemRandom
import hashlib


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
        NackReason.NOT_SET: 0,                   # extension NDNLPv2 compatible
        NackReason.CONGESTION: 50,                  # NDNLPv2 compatible
        NackReason.DUPLICATE: 100,                  # NDNLPv2 compatible
        NackReason.NO_ROUTE: 150,                   # NDNLPv2 compatible
        NackReason.NO_CONTENT: 160,                 # extension: does not exist in NDNLPv2
        NackReason.COMP_QUEUE_FULL: 161,            # extension: does not exist in NDNLPv2
        NackReason.COMP_PARAM_UNAVAILABLE: 162,     # extension: does not exist in NDNLPv2
        NackReason.COMP_EXCEPTION: 163,             # extension: does not exist in NDNLPv2
        NackReason.COMP_TERMINATED: 164,            # extension: does not exist in NDNLPv2
        NackReason.COMP_NOT_RUNNING: 165,           # extension: does not exist in NDNLPv2
        NackReason.COMP_NOT_PARSED: 166,            # extension: does not exist in NDNLPv2
        NackReason.PIT_TIMEOUT: 167,                # extension: does not exist in NDNLPv2
    }
    """Mapping of NackReason Enum to wire format values"""

    __nack_reason_enum = {
          0: NackReason.NOT_SET,                    # extension: does not exist in NDNLPv2
         50: NackReason.CONGESTION,                 # NDNLPv2 compatible
        100: NackReason.DUPLICATE,                  # NDNLPv2 compatible
        150: NackReason.NO_ROUTE,                   # NDNLPv2 compatible
        160: NackReason.NO_CONTENT,                 # extension: does not exist in NDNLPv2
        161: NackReason.COMP_QUEUE_FULL,            # extension: does not exist in NDNLPv2
        162: NackReason.COMP_PARAM_UNAVAILABLE,     # extension: does not exist in NDNLPv2
        163: NackReason.COMP_EXCEPTION,             # extension: does not exist in NDNLPv2
        164: NackReason.COMP_TERMINATED,            # extension: does not exist in NDNLPv2
        165: NackReason.COMP_NOT_RUNNING,           # extension: does not exist in NDNLPv2
        166: NackReason.COMP_NOT_PARSED,            # extension: does not exist in NDNLPv2
        167: NackReason.PIT_TIMEOUT,                # extension: does not exist in NDNLPv2
    }
    """Mapping of wire format nack reasons to NackReason Enum"""

    def __init__(self, log_level=255,identity_loator=None, publicKey=None):
        super().__init__(logger_name="NdnTlvEnc", log_level=log_level)


    #todo expression
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


    ### Helpers ###
    def encode_signature(self, sig) -> bytearray:
        """
        :param signature
        :return
        """


        encoder = TlvEncoder()

        # encoder_sig.writeOptionalBlobTlv(Tlv.SignatureValue,sig.to_string())#wrong parameter type
        # encode_sinature()
        encoder.writeOptionalBlobTlv(Tlv.SignatureValue, sig.to_bytearray())
        return encoder.getOutput()#.tobytes()



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


    def get_signature(self,private_key, packet_without_sig, payload: bytearray, name: Name, signature: Signature,inputByteArray=None):
        """

        :param packet_without_sig, payload (bytes) ,name
        :param signature, the Identity locator and input proviniance can not be calculated.
        :return: Signature, default Signature or proviniance signature (calculates identity proof, output signature and signaturesignature
        """
        #encoder = TlvEncoder()



        if (signature.signatureType == SignatureType.DEFAULT_SIGNATURE):
            m = hashlib.sha256()
            m.update(packet_without_sig[:-32])
            sig = m.digest()
            #only set outputSignature
            return Signature(SignatureType.DEFAULT_SIGNATURE, None, None, sig, None, None)

        elif (signature.signatureType == SignatureType.PROVENIENCE_SIGNATURE):


            # output signature
            m = hashlib.sha256()
            m.update(payload)
            signature.outputSignature = m.digest()
            #encoder.writeBlobTlv(Tlv.SignatureValue, outputSig)

            # identity proof
            m2 = hashlib.sha256()
            namebytearr=bytearray()
            namebytearr.extend(name.to_string().encode())
            m2.update(payload+namebytearr)
            #m.update(expression)
            signature.identityProof = m2.digest()

            #encoder.writeBlobTlv(Tlv.SignatureValue, identityProof)





            # TODO key locator, Signature provenience, SigSig
            return signature

        else:
            #SignatureType.NO_SIGNATURE
            sig = Signature()  # empty signature
            return sig

    def encode_signature_info(self,signature_type)-> bytearray:
        """
        :param signature_type
        :return: signature info Tlv
        """
        signature_type_arr = [signature_type]
        len1 = [len(signature_type_arr)]

        sig_info= [Tlv.SignatureInfo]+len1+signature_type_arr
        len2=[len(sig_info)]
        #len2 = [0]
        sig_info = [Tlv.SignatureType] + len1 + signature_type_arr
        return bytearray(sig_info)

    def encode_data(self, name: Name, payload: bytearray, private_key=2,
                    signature_type=SignatureType.NO_SIGNATURE, identity_locator=None, input_proveniance=None) -> bytearray:#signature
        """
        Assembly a data packet including a signature according to NDN packet format specification 0.3 (DigestSha256).
        :param name: Name
        :param payload: Payload
        :param signature_type
        :param identity_locator (optional)
        :param input_proveniance (optionyl)
        :return: Data-TLV
        """
        encoder = TlvEncoder()

        # Add signature (DigestSha256, zeroed)

        signature = Signature(signature_type,identity_locator,None,None,input_proveniance)


        #for testing
        #TODO remove
        signature.signatureType = SignatureType.PROVENIENCE_SIGNATURE
        #signature.signatureType = SignatureType.DEFAULT_SIGNATURE

        if(signature.signatureType!=SignatureType.PROVENIENCE_SIGNATURE):
             # signature value to set later
             signatureLength=32
        else:
            #get signatur (.provenience) as input?
            #TODO calc and add length provenience and keylocator?
            signatureLength=128
            # signature value to set later

        # empty field for signature, fill in later
        encoder.writeBlobTlv(Tlv.SignatureValue, bytearray(signatureLength))
        # fill in signature info
        signature_info = self.encode_signature_info(signature.signature_type_as_int())
        signature_info_len = len(signature_info)
        encoder.writeBlobTlv(Tlv.SignatureInfo, signature_info)

        encoder.writeTypeAndLength(Tlv.Signature,(signatureLength+signature_info_len))

        # Add content
        encoder.writeBlobTlv(Tlv.Content, payload)
        # Add meta info (empty)
        encoder.writeTypeAndLength(Tlv.MetaInfo, 0)
        # Add name
        encoder.writeBuffer(self.encode_name(name))
        # Add data type and len
        encoder.writeTypeAndLength(Tlv.Data, len(encoder))

        # Add signature value
        packet_without_sig = encoder.getOutput().tobytes()


        sig = self.get_signature(private_key,packet_without_sig, payload, name, signature )

        packet_with_sig = packet_without_sig[:-(signatureLength)]# + sig#.tobytes()

        encoded_sig=self.encode_signature(sig)
        packet_with_sig = packet_with_sig + encoded_sig

        return packet_with_sig


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
        if interest.wire_format is None:
            interest._wire_format = self.encode(interest)
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

        print(comps)
        print(dgest)
        print(Name(suite='ndn2013').__add__(comps))

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

    def decode_signature_component(self, decoder: TlvDecoder) -> bytearray:
        """
        Decode a signature component, e.g. signature info, signature value
        :param decoder: Decoder
        :return: Value of signature component
        """

        savePosition = decoder.getOffset()
        type = decoder.readVarNumber()
        decoder.seek(savePosition)
        return decoder.readBlobTlv(type).tobytes()

    def decode_signature(self, decoder: TlvDecoder) -> Signature:
        """
        decode signature
        :param decoder:
        :return: Signature
        """
        # TODO implement


        #endOffset = decoder.readNestedTlvsStart(Tlv.SignatureType)
        endOffset = decoder.readNestedTlvsStart(Tlv.Signature)#21
        offset = decoder.getOffset()

        sign_info = self.decode_signature_component(decoder)
        # sign = decoder.readBlobTlv(Tlv.ProvenienceSignature)
        # sign = sign.tobytes()

        print("<<<<<<sign_info")
        print(sign_info)

        #todo verify signature
        if sign_info==b'\x1b\x01\x02':
            #is PROVENIENCE_SIGNATURE
            sign = self.decode_signature_component(decoder)

        elif sign_info == b'\x1b\x01\x01':
            # is DEFAULT_SIGNATURE
            sign = self.decode_signature_component(decoder)

        else:
            #no signature
            sign = self.decode_signature_component(decoder)

        print("<<<<sign")
        print(sign)

        """
        #while  offset < endOffset:
        #if decoder.peekType(Tlv.ProvenienceSignature, endOffset):
        if decoder.peekType(Tlv.Signature, endOffset):
            print("<<<<<<<<<<<<<<<<<decoder.peekType(Tlv.ProvenienceSignature, endOffset): is true")

            sign_info=self.decode_signature_component(decoder)
            #sign = decoder.readBlobTlv(Tlv.ProvenienceSignature)
            #sign = sign.tobytes()
            print("sign_component")
            print(sign_info)
            sign=self.decode_signature_component(decoder)
            print("sign")
            print(sign)

        elif decoder.peekType(Tlv.SignatureType, endOffset):
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<2")
            #todo implement
            sign = Signature()
        else:
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<else")
            sign = Signature()  # empty
        """
        # sign=Signature()

        #decoder.finishNestedTlvs(endOffset)
        return sign


    def decode_data(self, input: bytearray) -> ([bytearray], bytearray):
        """
        Decodes a data packet
        :param input: Data packet in NDN-TLV wire format
        :return: Name and payload
        """

        print("<<<<<<<<<<<<input")
        print(input)

        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.Data)

        name = self.decode_name(decoder)
        self.decode_meta_info(decoder)

        payload = decoder.readBlobTlv(Tlv.Content).tobytes()

        #before payload
        signature=self.decode_signature(decoder)



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
            reason = self.__nack_reason_enum[wire_reason]
        except ValueError:
            # happens when nack reason is not specified
            reason = NackReason.NOT_SET
        return (name, reason)

    #def is_signature(self, input: bytearray) -> bool:




    def is_content(self, input: bytearray) -> bool:
        """
        Checks if content object packet
        :param input:  Packet in NDN-TLV wire format
        :return: True if content object
        """
        try:
            return input[0] == Tlv.Data
        except:
            return False

    def is_interest(self, input: bytearray) -> bool:
        """
        Checks if interest packet
        :param input:  Packet in NDN-TLV wire format
        :return: True if interest
        """
        try:
            return input[0] == Tlv.Interest
        except:
            return False

    def is_nack(selfself, input: bytearray) -> bool:
        """
        Checks if NACK packet
        :param input:  Packet in NDN-TLV wire format
        :return: True if NACK
        """
        try:
            return input[0] == 0x64 and input[3] == 0x03 and input[4] == 0x20
        except:
            return False
