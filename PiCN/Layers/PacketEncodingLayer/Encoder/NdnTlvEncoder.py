"""NDN TLV Encoder"""

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Nack, NackReason, Name, UnknownPacket, Signature, SignatureType

from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv

from random import SystemRandom
import hashlib
import os
import Crypto
from Crypto.PublicKey import RSA
from Crypto import Random
import ast


from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter


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

    def __init__(self, log_level=255,identity_loator=None):
        super().__init__(logger_name="NdnTlvEnc", log_level=log_level)


    #todo expression
    def encode(self, packet: Packet, key_location=None) -> bytearray:
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
                return self.encode_data(packet.name, packet.get_bytes(), key_location=key_location)
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
    def read_priv_key(self,path):
        """
        read private key from filesystem
        :param path: File system path to privat key (string)
        :return: private key (bytes)
        :raise an error if the file is not found
        """
        # read private key from file system and return (converted to appropriate format)
        if type(path) is not type(None):
            if path[-1:] is not '/':
                path += '/'

        if path is None:
            # relative path
            fileDir = os.path.dirname(os.path.abspath(__file__))
            parentDir=fileDir
            for i in range(3):
                parentDir = os.path.dirname(parentDir)

            path = os.path.join(parentDir, 'keys')  # Get the directory for StringFunctions
            path += '/'

        if not os.path.isfile(path + 'key.pub'):
            raise ValueError('no file found: ' + path + "key.pub doesn't exist")

        f = open(path + 'key.priv', 'br')
        return f.read()

    def read_pub_key(self,path):
        """
        read public key from file system
        :param: path: File system path to privat key (string)
        :return: public key (bytes)
        :raise an error if the file is not found
        """
        # correct missing / in filelocation input
        if type(path) is not type(None):
            if path[-1:] is not '/':
                path += '/'
        if not os.path.isfile(path + 'key.pub'):
            raise ValueError('no file found: '+path+"key.pub doesn't exist")

        f = open(path + 'key.pub', 'br')
        return f.read()

    def sign(self,data, priv_key):
        """

        :param data: (bytes)
        :param priv_key: private key from Crypto
        :return: signed data
        """
        key = RSA.importKey(priv_key)
        sig = key.sign(data, 32)

        return sig

    def verify(self,test_content, sig, pub_key):
        """
        :param test_content: the expected signature
        :param sig: signed data
        :param pub_key: public key from Crypto
        :return: (bool)
        """
        key = RSA.importKey(pub_key)
        encrypted = key.verify(test_content, sig)

        return encrypted

    def encode_signature(self, sig:Signature, key_location) -> bytearray:
        """
        :param signature (Signature)
        :param key_location: File system path to privat key (string)
        :return encoded and signed signature a tlv packet
        """
        encoder = TlvEncoder()

        # encoder_sig.writeOptionalBlobTlv(Tlv.SignatureValue,sig.to_string())#wrong parameter type
        # encode_sinature()

        if type(sig) is tuple:
            (sig,_)=sig

        if sig is None:
            print("Signature is none")
            return None

        if(sig.signatureType==SignatureType.PROVENANCE_SIGNATURE):
            private_key=self.read_priv_key(key_location)

            singed_sigsig=self.sign(sig.signatureSignature,private_key)[0]
            b_signed_sigsig=singed_sigsig.to_bytes((singed_sigsig.bit_length() + 7) // 8,byteorder='big')
            encoder.writeBlobTlv(Tlv.SignatureSignature, b_signed_sigsig)





            if sig.inputProvenance is not None:
                tlv_provenance=self.encode_signature(sig.inputProvenance,key_location)
                encoder.writeBlobTlv(Tlv.InputProviniance, tlv_provenance)
                if sig.argumentIdentifier is not None:
                    singed_argument_identifier = self.sign(sig.argumentIdentifier, private_key)[0]
                    b_singed_argument_identifier = singed_sigsig.to_bytes((singed_argument_identifier.bit_length() + 7) // 8, byteorder='big')
                    encoder.writeBlobTlv(Tlv.ArgumentIdentifier, b_singed_argument_identifier)
            else:
                encoder.writeBlobTlv(Tlv.InputProviniance, sig.inputProvenance)

            singed_output_signature = self.sign(sig.outputSignature, private_key)[0]
            b_singed_output_signature = singed_sigsig.to_bytes((singed_output_signature.bit_length() + 7) // 8, byteorder='big')
            encoder.writeBlobTlv(Tlv.OutputSignature, b_singed_output_signature)

            singed_identity_proof = self.sign(sig.identityProof, private_key)[0]
            b_singed_identity_proof = singed_sigsig.to_bytes((singed_identity_proof.bit_length() + 7) // 8, byteorder='big')
            encoder.writeBlobTlv(Tlv.IdentityProof, b_singed_identity_proof)
            #don't sign key locator
            encoder.writeBlobTlv(Tlv.KeyLocator, sig.identityLocator)

            #encoder.writeTypeAndLength(Tlv.SignatureValue, siglen)
            #encoder.writeOptionalBlobTlv(Tlv.SignatureValue, sig.to_bytearray())
            encoded_sig=encoder.getOutput()#.tobytes()

            return encoded_sig

        elif sig.signatureType is SignatureType.DEFAULT_SIGNATURE:
            pass
        else:
            pass

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


    def get_signature(self, packet_without_sig, payload: bytearray, name: Name, signature: Signature,inputByteArray=None):
        """
        :param packet_without_sig, payload (bytes) ,name
        :param signature (Identity locator and input proviniance can not be calculated)
        :return: Signature, default Signature or proviniance signature (calculates identity proof, output signature and signaturesignature)
        """
        #encoder = TlvEncoder()



        if (signature.signatureType == SignatureType.DEFAULT_SIGNATURE):
            m = hashlib.sha256()
            m.update(packet_without_sig[:-32])
            sig = m.digest()
            #only set outputSignature
            return Signature(SignatureType.DEFAULT_SIGNATURE, None, None, sig, None, None)

        elif (signature.signatureType == SignatureType.PROVENANCE_SIGNATURE):
            """
            priv_key = self.get_keys(True)
            key = RSA.importKey(priv_key)

            encrypted = key.encrypt(b'encrypt this message', 32)

            print("\n encripted:")
            print(encrypted)
            """

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

            m = hashlib.sha256()
            m.update(signature.to_bytearray())
            signature.signatureSignature = m.digest()

            #encoder.writeBlobTlv(Tlv.SignatureValue, identityProof)


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
        """
        sig_type=bytearray(signature_type)
        encoder = TlvEncoder()
        encoder.writeBlobTlv(Tlv.SignatureInfo, sig_type)
        signature_info=encoder.getOutput().tobytes()
        #encoder.writeTypeAndLength()
        print("<<<<<<<<<<<<<<<<")
        print(signature_info)
        print("batearray sig type")
        print(sig_type)
        """

        signature_type_arr = [signature_type]
        len1 = [len(signature_type_arr)]

        #sig_info = [Tlv.SignatureInfo]+len1+signature_type_arr
        #len2=[len(sig_info)]
        #len2 = [0]
        sig_info = [Tlv.SignatureType] + len1 + signature_type_arr
        return bytearray(sig_info)

    def length_of_signature_parts(self, signature:Signature,sig_len):
        length = 12
        if signature.identityLocator is not None:
            length += sig_len
        if signature.identityProof is not None:
            length += sig_len
        if signature.outputSignature is not None:
            length += sig_len
        if signature.argumentIdentifier is not None:
            length += sig_len
        if signature.inputProvenance is not None:
            length += self.input_proveniance_lenth(signature.inputProvenance,sig_len)
        if signature.signatureSignature is not None:
            length += sig_len
        return length

    def input_proveniance_lenth(self, provenance: Signature, sig_len) -> int:
        """
        calculate the legth of the input proviniance
        :param provenance (Signature)
        :param sig_len (int) length of a sigature part
        :return: length: int length of the sub tlv
        """
        length = 0

        if provenance is None:# or type(provenance) is not 'PiCN.Packets.Signature.Signature':
            print("!!!provenance is none")
            return 2
        if type(provenance) is tuple:
            (provenance, _) = provenance

        #length+=2
        # type and length for the sub tlvs

        if type(provenance) is list:
            for p in provenance:
                length += self.length_of_signature_parts(p,sig_len)
        else:
            length += self.length_of_signature_parts(provenance,sig_len)
        """ 
        length += 10
        if provenance.identityLocator is not None:
            length += 32
        if provenance.identityProof is not None:
            length += 32
        if provenance.outputSignature is not None:
            length += 32
        if provenance.argumentIdentifier is not None:
            length += 34
        if provenance.inputProvenance is not None:

            length += self.input_proveniance_lenth(provenance.inputProvenance)
        if provenance.signatureSignature is not None:
            length += 32
        """

        return length

    def get_provenance_for_testing(self, payload, name, rec_depth=1):
        """
        only for testing the provenance signature.
        :param payload:
        :param name:
        :param rec_depth: numbers of added proviniances
        :return: tuple (encoded tlv proviniance signatures,argumentIdentifier)
        """
        m = hashlib.sha256()
        m.update(bytearray(name.to_string(), 'utf-8'))
        argumentIdentifier=m.digest()

        if rec_depth <= 0:
            return (None,argumentIdentifier)

        encodert = TlvEncoder()
        encodert.writeBlobTlv(Tlv.SignatureValue, bytearray(262))
        packet_without_sigt = encodert.getOutput().tobytes()

        rec_depth -= 1
        (provenance,_)=self.get_provenance_for_testing(payload, name, rec_depth)
        signature=Signature(SignatureType.PROVENANCE_SIGNATURE,None,None,None, provenance)

        if provenance is not None:

            signature.argumentIdentifier=argumentIdentifier

        return self.get_signature(packet_without_sigt, payload, name, signature), argumentIdentifier


#todo remove
    def get_keys(self,privat_key: bool):
        """
        reads key from file
        :param privat_key: True gor private key, False for public key
        :return: key
        """
        # relative path
        absFilePath = os.path.abspath(__file__)
        fileDir = os.path.dirname(os.path.abspath(__file__))
        for i in range(3) :
            fileDir = os.path.dirname(fileDir)
        newPath = os.path.join(fileDir, 'keys')  # Get the directory for StringFunctions
        newPath += '/'
        # sys.path.append(newPath)  # Add path into PYTHONPATH

        if privat_key:
            f = open(newPath + 'key.priv', 'br')
        else:
            f = open(newPath + 'key.pub', 'br')
        return f.read()

    def encode_data(self, name: Name, payload: bytearray, key_location=None,
                    signature_type=SignatureType.NO_SIGNATURE, identity_locator=None, input_provenance=None,argument_identifier=None) -> bytearray:#signature
        """
        Assembly a data packet including a signature according to NDN packet format specification 0.3 (DigestSha256).
        :param name: Name
        :param payload: Payload
        :param signature_type
        :param identity_locator (optional)
        :param input_provenance (optional)
        :param argumentIdentifier (optional)
        :return: Data-TLV
        """
        encoder = TlvEncoder()

        # Add signature (DigestSha256, zeroed)

        # for testing proviniance
        # TODO remove
        (input_provenance,argumentIdentifier) = self.get_provenance_for_testing(payload, name,2)

        #input_provenance=[input_provenance,input_provenance]

        #create signature, fill in given values, the rest is calculated when the tlv packet is filled
        signature = Signature(signature_type, identity_locator, None, None, input_provenance, None, argumentIdentifier)


        #for testing
        #TODO remove
        signature.signatureType = SignatureType.PROVENANCE_SIGNATURE
        #signature.signatureType = SignatureType.DEFAULT_SIGNATURE

        if(signature.signatureType!=SignatureType.PROVENANCE_SIGNATURE):
             # signature value to set later
             signatureLength=32
        else:
            #get signatur (.provenience) as input?
            #TODO calc and add length provenience and keylocator?
            #min length+ typ,length for sub tlv

            #length of a signatur path depends on key size
            priv_key=self.read_priv_key(key_location)
            sign=self.sign(b'test',priv_key)[0]
            b_sign = sign.to_bytes((sign.bit_length() + 7) // 8, byteorder='big')
            sig_len = len(b_sign) # old 32
            
            iden_loc_len = 0+2
            iden_proof_len = sig_len+2
            output_sig_len = sig_len+2
            input_proveniance_len = 0
            sigsig_len = sig_len+2

            signatureLength=iden_proof_len+output_sig_len+sigsig_len

            if signature.inputProvenance is None:
                signatureLength+=2
            else:
                argument_identifier_len = sig_len + 2
                signatureLength +=self.input_proveniance_lenth(signature.inputProvenance, sig_len)+argument_identifier_len

            if signature.identityLocator is None:
                signatureLength += iden_loc_len
            else:
                pass



            # signature value to set later

        # empty field for signature, fill in later
        encoder.writeBlobTlv(Tlv.SignatureValue, bytearray(signatureLength))
        # fill in signature info
        signature_info = self.encode_signature_info(signature.signature_type_as_int())
        #signature_info = self.encode_signature_info(signature.signatureType)



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

        sig = self.get_signature(packet_without_sig, payload, name, signature )

        packet_with_sig = packet_without_sig[:-(signatureLength)]# + sig#.tobytes()


        #encoded_sig=self.encode_signature(sig,signatureLength)
        encoded_sig = self.encode_signature(sig,key_location)

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
        #endOffset = decoder.readNestedTlvsStart(Tlv.SignatureType)
        endOffset = decoder.readNestedTlvsStart(Tlv.Signature)#21
        offset = decoder.getOffset()

        sign_info = self.decode_signature_component(decoder)
        # sign = decoder.readBlobTlv(Tlv.ProvenienceSignature)
        # sign = sign.tobytes()


        if sign_info==b'\x1b\x01\x02':
            #is PROVENIENCE_SIGNATURE
            sign = self.decode_signature_component(decoder)
            decoder_sig = TlvDecoder(sign)
            identity_locator=self.decode_signature_component(decoder_sig)
            identity_proof = self.decode_signature_component(decoder_sig)
            output_signature = self.decode_signature_component(decoder_sig)
            input_proveniance = self.decode_signature_component(decoder_sig)
            sig_sig = self.decode_signature_component(decoder_sig)


            return Signature(SignatureType.PROVENANCE_SIGNATURE, identity_locator, identity_proof, output_signature, input_proveniance, sig_sig)

            """
            
            endOffset = decoder_sig.readNestedTlvsStart(Tlv.Name)
            decoder_sig.peekType()
            """





        elif sign_info == b'\x1b\x01\x01':
            # is DEFAULT_SIGNATURE
            sign = self.decode_signature_component(decoder)
            return Signature(SignatureType.DEFAULT_SIGNATURE,None,None,sign)

        else:
            #no signature
            sign = self.decode_signature_component(decoder)
            return Signature(SignatureType.NO_SIGNATURE,None,None,sign)


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

    def verify_signature(self, name:Name, meta_info, payload, signature_in: Signature, public_key=2):
        """

        :param name:
        :param meta_info:
        :param payload:
        :param signature_in: signature from receved packet, values are hashed
        :param public_key:
        :return type: bool, if signature is correct
        """
        #TODO get public key

        #self.encode_data(name,payload,)
        signature_calculated=Signature(signature_in.signatureType)
        #signature_calculated.identityLocator=signature_in.identityLocator

        m = hashlib.sha256()
        name_bytearr = bytearray()
        name_bytearr.extend(name.to_string().encode())
        m.update(payload + name_bytearr)
        signature_calculated.identityProof = m.digest()

        m = hashlib.sha256()
        m.update(payload)
        signature_calculated.outputSignature = m.digest()

        # todo Proviniance signature

        m = hashlib.sha256()
        m.update(signature_calculated.to_bytearray())
        signature_calculated.signatureSignature = m.digest()

        if(signature_calculated.identityProof!=signature_in.identityProof):
            print("IDENTITY PROOF IS NOT CORRECT!")
            return False
        if (signature_calculated.outputSignature != signature_in.outputSignature):
            print("OUTPUT SIGNATURE IS NOT CORRECT!")
            return False
        if (signature_calculated.signatureSignature != signature_in.signatureSignature):
            print("SIGNATURE SIGNATURE IS NOT CORRECT!")
            return False

        return True




    def decode_data(self, input: bytearray) -> ([bytearray], bytearray):
        """
        Decodes a data packet
        :param input: Data packet in NDN-TLV wire format
        :return: Name and payload
        """



        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.Data)

        name = self.decode_name(decoder)
        meta_info=self.decode_meta_info(decoder)

        payload = decoder.readBlobTlv(Tlv.Content).tobytes()

        #before payload
        signature=self.decode_signature(decoder)

        #TODO ENCRIPT SIGNATURE

        signature_is_correct=self.verify_signature(name,meta_info,payload,signature)

        print("<<<<<<<<<sig corect?")
        print(signature_is_correct)


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



