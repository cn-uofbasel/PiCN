# client who can request data, uses reputation of contetnt provider to request data from most trustworthy node.

import argparse
import socket
import sys
import hashlib
import random

from PiCN.ProgramLibs.ReputationClient.ReputationClient import ReputationClient
from PiCN.ReputationSystem.ReputationSystem import reputationSystem
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Interest, Content
import os
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCN.Packets import Packet, Content, Interest, Nack, NackReason, Name, UnknownPacket, Signature, SignatureType
import VerifyProvenance
#from PiCN.Executable.VerifyProvenance import VerifyProvenance

#new using the ProgramLibs.ReputationClient
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='client who ceeps track of the reputation of other nodes')
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1',
                        help="IP address or hostname of forwarder (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=9500, help="UDP port (default: 9500)")
    parser.add_argument('-n', '--myname', type=str, default="/user1/", help="my name (default: /user1/)")
    parser.add_argument('-k', '--keylocation', type=str, help="Location of the key files (default: ~PiCN/identity/)",
                        default="~/PiCN/identity/")

    args = parser.parse_args()
    repclient = ReputationClient(args)
    repclient.reputationClientMain(args)
