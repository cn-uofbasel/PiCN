"""PiCN Peek: Tool to lookup a single content object"""

import argparse
import socket
import sys

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Interest, Content
import os


def main(args):

    key_location=correct_path_input(args.keylocation)
    output_location=correct_path_input(args.output_location)

    # Packet encoder
    encoder = NdnTlvEncoder() if args.format == 'ndntlv' else SimpleStringEncoder

    # Generate interest packet
    interest: Interest = Interest(args.name)
    encoded_interest = encoder.encode(interest)

    # Send interest packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(args.timeout)
    sock.bind(("0.0.0.0", 0))
    try:
        resolved_hostname = socket.gethostbyname(args.ip)
    except:
        print("Resolution of hostname failed.")
        sys.exit(-2)
    sock.sendto(encoded_interest, (resolved_hostname, args.port))

    # Receive content object
    try:
        wire_packet, addr = sock.recvfrom(8192)
    except:
        print("Timeout.")
        sys.exit(-1)

    # Print
    if args.plain is False:
        print("<<<<<<<<<<<<<<<<<<<<<< peek not decode data")

        printer = NdnTlvPrinter(wire_packet)
        printer.formatted_print()
    else:
        encoder = NdnTlvEncoder(file_location=key_location)
        if encoder.is_content(wire_packet):
            print("<<<<<<<<<<<<<<<<<<<<<< peek decodes data")

            #print(os.listdir(output_location))
            """
            if not os.path.exists(output_location):
                with open(output_location, 'w+'): pass
            """
            f = open(output_location + 'content_object', 'wb+')
            f.write(wire_packet)
            f.close()
            print("Contetn Object saved to " + output_location + 'content_object')



            sys.stdout.buffer.write(encoder.decode_data(wire_packet)[1])
        else:
            sys.exit(-2)

def correct_path_input(filepath):
    # correct missing / in key_content_obj_location input
    if type(filepath) is not type(None):
        if filepath[-1:] is not '/':
            filepath += '/'
    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Peek Tool')
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1', help="IP address or hostname of forwarder (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-t', '--timeout', type=int, default=5, help="Timeout (default: 5)")
    parser.add_argument('-f', '--format', choices=['ndntlv','simple'], type=str, default='ndntlv', help='Packet Format (default: ndntlv)')
    parser.add_argument('--plain', help="plain output (writes payload to stdout or returns -2 for NACK)", action="store_true")
    parser.add_argument('name', type=str, help="CCN name of the content object to fetch")
    parser.add_argument('-k', '--keylocation', type=str, help="Location of the key files (default: ~PiCN/identity/)",
                        default="~/PiCN/identity/")
    parser.add_argument('-o', '--output_location', type=str, help="Location of the file where the content object is stored (default: ~PiCN/identity/)",
                        default="~/PiCN/identity/")

    args = parser.parse_args()
    main(args)