"""PiCN Peek: Tool to lookup a single content object"""

import argparse
import base64
import socket
import sys

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Interest, Content, Name

def read_content(name):
    file = open(name, "r")
    return file.read()

def unescape_str_to_Name(name: str) -> Name:
    r = []
    if '[' not in name or ']' not in name:
        return Name(name)
    tmp_comps1 = name.split('[')
    tmp_comps2 = tmp_comps1[1].split(']')
    if tmp_comps1[0].endswith("/"):
        tmp_comps1[0] = tmp_comps1[0][:-1]
    if tmp_comps2[1].startswith("/"):
        tmp_comps2[1] = tmp_comps2[1][1:]
    comps = [tmp_comps1[0], tmp_comps2[0], tmp_comps2[1]]

    name = Name(comps[0])
    name += comps[1]
    name += comps[2]

    return name


def main(args):

    # Packet encoder
    encoder = NdnTlvEncoder() if args.format == 'ndntlv' else SimpleStringEncoder

    # Generate interest packet
    name_str = args.name
    name_str = name_str.replace(", ", ",")
    if args.code is not None and "#" in name_str:
        try:
            f_content = read_content(args.code)
        except:
            print("Could not open file!")
            return
        base64_content = '"BASE64:' + base64.b64encode(f_content.encode()).decode() + '"'
        name_str = name_str.replace('#', base64_content)
    name = unescape_str_to_Name(name_str)

    interest: Interest = Interest(name)
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
        printer = NdnTlvPrinter(wire_packet)
        printer.formatted_print()
    else:
        encoder = NdnTlvEncoder()
        if encoder.is_content(wire_packet):
            sys.stdout.buffer.write(encoder.decode_data(wire_packet)[1])
        elif encoder.is_nack(wire_packet):
            sys.stdout.buffer.write(str("Nack Received: ").encode() + str(encoder.decode_nack(wire_packet)[1]).encode())
        else:
            sys.exit(-2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Peek Tool')
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1', help="IP address or hostname of forwarder (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-t', '--timeout', type=int, default=5, help="Timeout (default: 5)")
    parser.add_argument('-f', '--format', choices=['ndntlv','simple'], type=str, default='ndntlv', help='Packet Format (default: ndntlv)')
    parser.add_argument('--plain', help="plain output (writes payload to stdout or returns -2 for NACK)", action="store_true")
    parser.add_argument('--code', help="file which contains python code for named functions")
    parser.add_argument('name', type=str, help="CCN name of the content object to fetch")
    args = parser.parse_args()
    main(args)