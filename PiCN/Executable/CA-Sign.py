"""tool to sign public key object with ca key"""
import os
import argparse
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Name
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv
import hashlib
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from Crypto.PublicKey import RSA
from Crypto import Random



def main(args):
    key_content_obj_location=correct_fileinput(args.key_content_obj_location)
    ca_priv_key_location = correct_fileinput(args.ca_priv_key_location)
    key_content_obj_location=find_default_path(key_content_obj_location,"keys")
    ca_priv_key_location=find_default_path(ca_priv_key_location,"CAkeys")

    f = open(key_content_obj_location + 'pubkey.ca', 'rb')
    pubkey_ca=f.read()
    f = open(ca_priv_key_location + 'CA_key.priv', 'rb')
    ca_priv_key = f.read()
    f = open(ca_priv_key_location + 'CA_key.pub', 'rb')
    ca_pub_key = f.read()


    printer = NdnTlvPrinter(pubkey_ca)
    printer.formatted_print()


    name, payload=decode_key(pubkey_ca)

    printer = NdnTlvPrinter(payload)
    printer.formatted_print()

    key = RSA.importKey(ca_priv_key)


    to_sign = name.to_string()+str(payload)+str(ca_priv_key)

    m = hashlib.sha256()
    m.update(bytes(to_sign, 'utf-8'))  #
    sig_h = m.digest()
    sig = key.sign(sig_h, 2)[0]




    content_obj_sig=encode_key(name,payload,ca_pub_key,str(sig))

    f = open(key_content_obj_location + 'public_key_signed_by_CA', 'wb')
    f.write(content_obj_sig)
    f.close()
    """
    printer = NdnTlvPrinter(content_obj_sig)
    printer.formatted_print()
    """

def decode_key(input: bytearray) -> ([bytearray], bytearray):
    decoder = TlvDecoder(input)
    decoder.readNestedTlvsStart(Tlv.Data)
    encoder=NdnTlvEncoder()
    name = encoder.decode_name(decoder)
    encoder.decode_meta_info(decoder)
    payload = decoder.readBlobTlv(Tlv.Content).tobytes()
    return (name, payload)


def encode_key(name: Name, pubkey, ca_key, ca_signature):
    encoder = TlvEncoder()
    # signature value to set later
    encoder.writeBlobTlv(Tlv.SignatureValue, bytearray(32))
    encoder.writeBlobTlv(Tlv.SignatureInfo, bytearray([Tlv.SignatureType, 1, 0]))

    encoder.writeBlobTlv(Tlv.Content, bytes(ca_signature,'utf-8'))
    encoder.writeBlobTlv(Tlv.Content, ca_key)
    encoder.writeBlobTlv(Tlv.Content, pubkey)
    """
    for k in pubkey:
        encoder.writeBlobTlv(Tlv.Content, k)
    """

    encoder.writeTypeAndLength(Tlv.MetaInfo, 0)

    # Add name
    ndntlvencoder=NdnTlvEncoder()
    encoder.writeBuffer(ndntlvencoder.encode_name(name=name))
    # Add data type and len
    encoder.writeTypeAndLength(Tlv.Data, len(encoder))
    # Add signature value
    packet_without_sig = encoder.getOutput().tobytes()
    m = hashlib.sha256()
    m.update(packet_without_sig[:-32])
    sig = m.digest()
    packet_with_sig = packet_without_sig[:-32] + sig
    return packet_with_sig


def find_default_path(path,name):
    if path is None:
        # relative path
        fileDir = os.path.dirname(os.path.abspath(__file__))
        # print(fileDir)
        parentDir = os.path.dirname(fileDir)
        # print(parentDir)
        newPath = os.path.join(parentDir, name)  # Get the directory for StringFunctions
        # print(newPath)
        newPath += '/'
        # sys.path.append(newPath)  # Add path into PYTHONPATH
        return newPath
    else:
        return path

def correct_fileinput(filepath):
    # correct missing / in key_content_obj_location input
    if type(filepath) is not type(None):
        if filepath[-1:] is not '/':
            filepath += '/'
    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Key Generator Tool')
    parser.add_argument('-f', '--key_content_obj_location', type=str, help="Location of the contet object files (default: /PiCN/keys/)")
    parser.add_argument('-c', '--ca_priv_key_location', type=str,help="Location of the ca private key (default: /PiCN/CAkeys/)")

    args = parser.parse_args()
    main(args)