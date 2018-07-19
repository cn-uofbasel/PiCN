"""Heartbeat Generator"""

import argparse
import socket
import sys
import time

from PiCN.Playground.Heartbeats.Layers.PacketEncoding import ExtendedNdnTlvEncoder
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import Heartbeat


def main(args):
    # Packet encoder
    encoder = ExtendedNdnTlvEncoder()

    # Generate heartbeat packet
    heartbeat: Heartbeat = Heartbeat(args.name)
    encoded_heartbeat = encoder.encode(heartbeat)

    # Send heartbeat packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.bind(("0.0.0.0", 0))
    try:
        resolved_hostname = socket.gethostbyname(args.ip)
    except:
        print("Resolution of hostname failed.")
        sys.exit(-2)
    sock.sendto(encoded_heartbeat, (resolved_hostname, args.port))

    if args.interval is not None:
        while True:
            time.sleep(args.interval)
            sock.sendto(encoded_heartbeat, (resolved_hostname, args.port))
            print('.', end='', flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Peek Tool')
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1',
                        help="IP address or hostname of forwarder (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-t', '--interval', type=int, required=False,
                        help="Heartbeat interval in seconds (only one heartbeat is sent if unspecified)")
    parser.add_argument('name', type=str, help="CCN name of the content object to fetch")
    args = parser.parse_args()
    main(args)
