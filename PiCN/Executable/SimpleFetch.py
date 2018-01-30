"""Lookup a content object"""

import argparse
import socket
import sys

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Content, Interest


def main(args):

    # Packet encoder
    encoder = NdnTlvEncoder() if args.suite == 'ndntlv' else SimpleStringEncoder

    # Generate interest packet
    interest: Interest = Interest(args.name)
    encoded_interest = encoder.encode(interest)

    # Send interest packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.bind(("0.0.0.0", 0))
    sock.sendto(encoded_interest, (args.ip, args.port))

    # Receive content object
    try:
        encoded_content, addr = sock.recvfrom(8192)
    except:
        print("Timeout.")
        sys.exit(-1)

    # Print
    try:
        content: Content = encoder.decode(encoded_content)
        printer = NdnTlvPrinter(content.wire_format)
        printer.formatted_print()
    except:
        print("Received packet can not be parsed.")
        sys.exit(-2)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lookup a CCN Packet')
    parser.add_argument('--suite', choices=['ndntlv',' simple'], type=str, default='ndntlv', help='default is: "ndntlv"')
    parser.add_argument('ip',   type=str, help="IP addr of forwarder")
    parser.add_argument('port', type=int, help="UDP port of forwarder")
    parser.add_argument('name', type=str, help="ICN name of content to fetch")
    args = parser.parse_args()
    main(args)