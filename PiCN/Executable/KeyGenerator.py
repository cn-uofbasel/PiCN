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

    #correct missing / in keylocation input
    if type(args.keylocation) is not type(None):
        if args.keylocation[-1:] != '/':
            args.keylocation+='/'

    if args.len < 1024:
        print("Key length to smal, set to 1024.")
        args.len=1024

    f = open(args.ca_pub_key_location + 'CA_key.pub', 'rb')
    ca_pub_key = f.read()

    random_generator = Random.new().read
    key = RSA.generate(args.len, random_generator)  # generate pub and priv key

    """
    public_key = key.exportKey('DER')
    private_key = key.exportKey('DER', 8)
    """

    public_key = key.publickey().exportKey('PEM').decode('ascii')
    private_key = key.exportKey('PEM').decode('ascii')

    """
    if args.keylocation is None:
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
        newPath=args.keylocation
    """
    if (os.path.isfile(args.keylocation+'key.pub') or os.path.isfile(args.keylocation+'key.priv')) and args.overwrite is False:
        print("Key file already exists. \nChange keylocation or allow to overwrite!\nNo keys generated!")
        exit()


    key_tlv=encode_key(args.keylocation, Name(args.name),public_key,ca_key=ca_pub_key)



    print(type(key_tlv))

    try:
        os.makedirs(args.keylocation)
    except FileExistsError:
        # directory already exists, do nothing
        pass

    f = open(args.keylocation + 'pubkey.ca', 'w+b')
    f.write(key_tlv)
    print("content object saved to " + args.keylocation + 'pubkey.ca')
    f.close()

    f = open(args.keylocation+'key.pub', 'w+')
    f.write(public_key)
    print("Public key saved to " +args.keylocation+'key.pub')
    f.close()
    f = open(args.keylocation+'key.priv', 'w+')
    f.write(private_key)
    print("Private key saved to "+args.keylocation+'key.priv')
    f.close()
    print("Done.")

    printer = NdnTlvPrinter(key_tlv)
    printer.formatted_print()


def encode_key(keylocation, name: Name, pubkey, ca_signature=bytearray(128),ca_key=bytearray(128)):
    encoder = TlvEncoder()
    # signature value to set later
    encoder.writeBlobTlv(Tlv.SignatureValue, bytearray(32))
    encoder.writeBlobTlv(Tlv.SignatureInfo, bytearray([Tlv.SignatureType, 1, 0]))

    encoder2 = TlvEncoder()

    encoder2.writeBlobTlv(Tlv.ContentType_Key, ca_signature)
    encoder2.writeBlobTlv(Tlv.ContentType_Key, ca_key)
    encoder2.writeBlobTlv(Tlv.ContentType_Key, bytes(pubkey,'utf-8'))
    encoder.writeBlobTlv(Tlv.Content, encoder2.getOutput())

    """
    for k in pubkey:
        encoder.writeBlobTlv(Tlv.Content, k)
    """

    encoder.writeTypeAndLength(Tlv.MetaInfo, 0)

    # Add name
    ndntlvencoder=NdnTlvEncoder(file_location=keylocation)
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
    parser.add_argument('-k', '--keylocation', type=str, help="Location of the key files (default: ~PiCN/identity/)",default="~/PiCN/identity/")
    parser.add_argument('-o', '--overwrite', action='store_true', help="Overwrite keys (if already existing)")
    parser.add_argument('-n', '--name', type=str, help="name of key content object (default: /PiCN/keys/)",default="/PiCN/keys")
    parser.add_argument('-c', '--ca_pub_key_location', type=str, help="Location of the ca public key (default: ~PiCN/CA/)", default="~/PiCN/CA/")

    args = parser.parse_args()

    print(args.keylocation)

    main(args)
