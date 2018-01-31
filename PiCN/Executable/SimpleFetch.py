"""Lookup a content object"""

import argparse
import socket
import sys

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Interest



def main(args):

    # Packet encoder
    encoder = NdnTlvEncoder() if args.format == 'ndntlv' else SimpleStringEncoder

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
    printer = NdnTlvPrinter(encoded_content)
    printer.formatted_print()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Peek Tool')
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1', help="IP address of forwarder (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-f', '--format', choices=['ndntlv','simple'], type=str, default='ndntlv', help='Packet Format (default: ndntlv)')
    parser.add_argument('name', type=str, help="CCN name of the content object to fetch")
    args = parser.parse_args()
    main(args)