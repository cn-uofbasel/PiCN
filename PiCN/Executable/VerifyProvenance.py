
import argparse
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Name
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv
import hashlib
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Packets import Packet, Content, Interest, Nack, NackReason, Name, UnknownPacket, Signature, SignatureType
from Crypto.PublicKey import RSA
import time

def main(args):
    #content_obj_location = correct_path_input(args.content_obj_location)

    #f = open(content_obj_location+"content_object", 'rb')

    f = open(args.content_obj_location, 'rb')
    wire_data = f.read()




    encoder = TlvEncoder()
    #encoder.writeBlobTlv(Tlv.InputProviniance, wire_data)
    encoder.writeBuffer(wire_data)
    a = encoder.getOutput().tobytes()
    printer = NdnTlvPrinter(a)
    printer.formatted_print()
    time.sleep(0.7)



    #encoder = NdnTlvEncoder()
    (name, payload, signature) = decode_data(wire_data)

    #print(payload)
    #print(type(payload))

    verify_signature(name, payload, signature, wire_data, args)

def decode_data(input: bytearray) -> ([bytearray], bytearray):
        """
        Decodes a data packet
        :param input: Data packet in NDN-TLV wire format
        :return: Name and payload
        """
        ndntlvencoder = NdnTlvEncoder()
        decoder = TlvDecoder(input)
        decoder.readNestedTlvsStart(Tlv.Data)

        name = ndntlvencoder.decode_name(decoder)
        meta_info=ndntlvencoder.decode_meta_info(decoder)

        payload = decoder.readBlobTlv(Tlv.Content).tobytes()
        #before payload
        signature=ndntlvencoder.decode_signature(decoder)
        #signature_is_correct=self.verify_signature(name,meta_info,payload,signature)
        #return (name, payload, signature)
        return (name, payload,signature)

def verify_signature(name: Name,  payload, signature_in: Signature,wire_data,args):
    """
    :param name:name of content
    :param payload:
    :param signature_in: signature from received packet
    :return type: bool, if signature is correct
    public key in signature
    """

    #calc new signature
    signature_calculated=calculate_new_signature(name,  payload, signature_in)
    #get pubic key
    (public_key,pubkey_ca_content_obj,public_key_ca)=extract_key(args,wire_data)
    #verifiy key
    key_is_ok=verify_key(pubkey_ca_content_obj)
    if key_is_ok:
        pass
    else:
        print("key not ok")
    if payload is b'3':
        print("Provenance Record is correct")
        return True
    elif payload is b'7':
        print("ERROR: Input Provenace is not correct")
        return False
    #if (signature_calculated.identityProof != signature_in.identityProof):
    elif(not verify(signature_calculated.identityProof,signature_in.identityProof,public_key)):
        print("IDENTITY PROOF IS NOT CORRECT!")
        return False
    if (signature_calculated.outputSignature != signature_in.outputSignature):
        print("OUTPUT SIGNATURE IS NOT CORRECT!")
        return False
    if (signature_calculated.signatureSignature != signature_in.signatureSignature):
        print("SIGNATURE SIGNATURE IS NOT CORRECT!")
        return False

    return True

def verify(test_content, sig, pub_key):
    """
    :param test_content: the expected signature
    :param sig: signed data
    :param pub_key: public key from Crypto
    :return: (bool)
    """

    key = RSA.importKey(pub_key)
    if type(sig) is "<class 'bytes'>":
        print("is bytes")
    sig = int.from_bytes(sig, 'little')
    if type(sig) is not 'tuple':
        sig=(sig,0)

    return key.verify(test_content, sig)



def verify_key(pubkey_ca_content_obj):
    #todo
    return True


def extract_key(args,wire_data):
    """
    :param args:
    :param wire_data:
    :return: (public key in content object, content object with pub key signed by CA)
    """
    f = open(args.keylocation + 'public_key_signed_by_CA', 'rb')
    pubkey_ca_content_obj = f.read()
    ndntlvdecoder = NdnTlvEncoder()
    decoder = TlvDecoder(pubkey_ca_content_obj)
    decoder.readNestedTlvsStart(Tlv.Data)
    key_name = ndntlvdecoder.decode_name(decoder)
    meta_info = ndntlvdecoder.decode_meta_info(decoder)
    key_payload = decoder.readBlobTlv(Tlv.Content).tobytes()

    decoder2 = TlvDecoder(key_payload)
    public_key=decoder2.readBlobTlv(Tlv.ContentType_Key).tobytes()
    public_key_ca = decoder2.readBlobTlv(Tlv.ContentType_Key).tobytes()
    return (public_key,pubkey_ca_content_obj,public_key_ca)

def calculate_new_signature(name: Name,  payload, signature_in: Signature):
    # self.encode_data(name,payload,)
    signature_calculated = Signature(signature_in.signatureType)
    # signature_calculated.identityLocator=signature_in.identityLocator
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
    return signature_calculated

def correct_path_input(filepath):
    # correct missing / in key_content_obj_location input
    if type(filepath) is not type(None):
        if filepath[-1:] is not '/':
            filepath += '/'
    return filepath

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Tool, to verify provenance')
    parser.add_argument('-o', '--content_obj_location', type=str,help="Location of the file where the content object is stored (default: ~PiCN/identity/)",
                            default="~/PiCN/identity/")
    parser.add_argument('-k', '--keylocation', type=str, help="Location of the key files (default: ~PiCN/identity/)",
                        default="~/PiCN/identity/")

    args = parser.parse_args()
    """
    some_string="Hello World"
    print(some_string.partition(' ')[0])
    """
    main(args)

