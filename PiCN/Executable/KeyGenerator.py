"""PiCN Peek: Tool to generate and store a key pair"""

import argparse
import Crypto
from Crypto.PublicKey import RSA
from Crypto import Random
import ast
import os, sys
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv
import hashlib
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Name

def main(args):

    #correct missing / in filelocation input
    if type(args.filelocation) is not type(None):
        if args.filelocation[-1:] is not '/':
            args.filelocation+='/'

    if args.len < 1024:
        print("Key length to smal, set to 1024.")
        args.len=1024

    random_generator = Random.new().read
    key = RSA.generate(args.len, random_generator)  # generate pub and priv key

    """
    public_key = key.exportKey('DER')
    private_key = key.exportKey('DER', 8)
    """

    public_key = key.publickey().exportKey('PEM').decode('ascii')
    private_key = key.exportKey('PEM').decode('ascii')


    if args.filelocation is None:
        #relative path
        fileDir = os.path.dirname(os.path.abspath(__file__))
        #print(fileDir)
        parentDir = os.path.dirname(fileDir)
        #print(parentDir)

        newPath = os.path.join(parentDir, 'keys')  # Get the directory for StringFunctions
        #print(newPath)
        newPath+='/'
        #sys.path.append(newPath)  # Add path into PYTHONPATH
    else:
        newPath=args.filelocation

    if (os.path.isfile(newPath+'key.pub') or os.path.isfile(newPath+'key.pub')) and args.overwrite is False:
        print("Key file already exists. \nChange filelocation or allow to overwrite!\nNo keys generated!")
        exit()


    key_tlv=encode_key(Name(args.name),public_key)
    """
    printer = NdnTlvPrinter(key_tlv)
    printer.formatted_print()

    print(type(key_tlv))
    """
    f = open(newPath + 'pubkey.ca', 'wb')
    f.write(key_tlv)
    print("content object saved to " + newPath + 'pubkey.ca')
    f.close()


    f = open(newPath+'key.pub', 'w')
    f.write(public_key)
    print("Public key saved to " +newPath+'key.pub')
    f.close()
    f = open(newPath+'key.priv', 'w')
    f.write(private_key)
    print("Private key saved to "+newPath+'key.priv')
    f.close()
    print("Done.")


def encode_key(name: Name, pubkey, ca_signature=bytearray(128),ca_key=bytearray(128)):
    encoder = TlvEncoder()
    # signature value to set later
    encoder.writeBlobTlv(Tlv.SignatureValue, bytearray(32))
    encoder.writeBlobTlv(Tlv.SignatureInfo, bytearray([Tlv.SignatureType, 1, 0]))

    encoder.writeBlobTlv(Tlv.Content, ca_signature)
    encoder.writeBlobTlv(Tlv.Content, ca_key)
    encoder.writeBlobTlv(Tlv.Content, bytes(pubkey,'utf-8'))
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Key Generator Tool')
    parser.add_argument('-l', '--len', type=int, default=1024, help="Length of the Key, (default: 1024, minimal: 1024, multiple of 256)")
    parser.add_argument('-f', '--filelocation', type=str, help="Location of the key files (default: /PiCN/keys/)")
    parser.add_argument('-o', '--overwrite', action='store_true', help="Overwrite keys (if already existing)")
    parser.add_argument('-n', '--name', type=str, help="name of key content object (default: /PiCN/keys/)",default="/PiCN/keys")

    args = parser.parse_args()
    main(args)
