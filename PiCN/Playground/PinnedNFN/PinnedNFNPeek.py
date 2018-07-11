"""Pinned NFN Peek"""

import argparse
import socket
import sys
import time

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Interest, Content


def main(args):

    # Packet encoder
    encoder = NdnTlvEncoder() if args.format == 'ndntlv' else SimpleStringEncoder

    # Generate interest packet
    first_interest: Interest = Interest(args.name)
    encoded_first_interest = encoder.encode(first_interest)

    # Send interest packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.bind(("0.0.0.0", 0))
    try:
        resolved_hostname = socket.gethostbyname(args.ip)
    except:
        print("Resolution of hostname failed.")
        sys.exit(-2)
    sock.sendto(encoded_first_interest, (resolved_hostname, args.port))

    # Receive content object
    try:
        wire_packet_first, addr = sock.recvfrom(8192)
    except:
        print("Timeout.")
        sys.exit(-1)

    # Wait
    time_to_wait = int(encoder.decode_data(wire_packet_first)[1])
    print("Waiting for result: " + str(time_to_wait))
    time.sleep(time_to_wait * 1.2)


    # Send second interest
    new_components = args.name.split("/")[1:-1]
    new_components.append("resultpNFN")
    new_name = "/" + '/'.join(new_components)
    second_interest: Interest = Interest(new_name)
    encoded_second_interest = encoder.encode(second_interest)
    sock.sendto(encoded_second_interest, (resolved_hostname, args.port))

    # Receive result
    try:
        wire_packet_second, addr = sock.recvfrom(8192)
    except:
        print("Timeout.")
        sys.exit(-1)

    # Print
    if args.plain is False:
        printer = NdnTlvPrinter(wire_packet_second)
        printer.formatted_print()
    else:
        encoder = NdnTlvEncoder()
        if encoder.is_content(wire_packet_second):
            sys.stdout.buffer.write(encoder.decode_data(wire_packet_second)[1] + b"\n")
        else:
            sys.exit(-2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Pinned NFN Peek Tool')
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1', help="IP address or hostname of forwarder (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-f', '--format', choices=['ndntlv','simple'], type=str, default='ndntlv', help='Packet Format (default: ndntlv)')
    parser.add_argument('--plain', help="plain output (writes payload to stdout or returns -2 for NACK)", action="store_true")
    parser.add_argument('name', type=str, help="Computation")
    args = parser.parse_args()
    main(args)
