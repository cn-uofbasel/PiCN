"""Heartbeat Peek"""

import argparse
import socket
import sys

from PiCN.Playground.Heartbeats.Layers.PacketEncoding import ExtendedNdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Interest


def main(args):
    # Packet encoder
    encoder = ExtendedNdnTlvEncoder()

    # Generate interest packet
    interest: Interest = Interest(args.name)
    encoded_interest = encoder.encode(interest)

    # Send interest packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(300)
    sock.bind(("0.0.0.0", 0))
    try:
        resolved_hostname = socket.gethostbyname(args.ip)
    except:
        print("Resolution of hostname failed.")
        sys.exit(-2)
    sock.sendto(encoded_interest, (resolved_hostname, args.port))

    # Receive heartbeat and content
    while True:
        try:
            wire_packet, addr = sock.recvfrom(8192)
        except:
            print("Timeout.")
            sys.exit(-1)
        if encoder.is_heartbeat(wire_packet):
            print("Heartbeat received...")
        elif encoder.is_content(wire_packet):
            if args.plain is False:
                printer = NdnTlvPrinter(wire_packet)
                printer.formatted_print()
                return
            else:
                sys.stdout.buffer.write(encoder.decode_data(wire_packet)[1])
                return
        else:
            print("Received unknown packet.")
            sys.exit(-3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Heartbeat Peek Tool')
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1',
                        help="IP address or hostname of forwarder (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('--plain', help="plain output (writes payload to stdout or returns -2 for NACK)",
                        action="store_true")
    parser.add_argument('name', type=str, help="CCN name of the content object to fetch")
    args = parser.parse_args()
    main(args)
