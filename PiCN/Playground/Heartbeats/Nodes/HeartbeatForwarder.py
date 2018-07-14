"""Heartbeat Forwarder executable"""

import argparse
import logging

from PiCN.Playground.Heartbeats.Nodes import HeartbeatForwarderStack
from PiCN.Logger import Logger
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import ExtendedNdnTlvEncoder


def main(args):
    # Log Level
    if args.logging == 'error':
        log_level = logging.ERROR
    elif args.logging == 'warning':
        log_level = logging.WARNING
    elif args.logging == 'info':
        log_level = logging.INFO
    elif args.logging == 'debug':
        log_level = logging.DEBUG
    else:
        log_level = 255
    logger = Logger("ICNForwarder", log_level)

    # Info
    logger.info("Starting a Heartbeat Nodes...")
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:   Extended NDN Packet Format")

    # Packet encoder
    encoder = ExtendedNdnTlvEncoder(log_level)

    # Start
    forwarder = HeartbeatForwarderStack(args.port, log_level, encoder)
    forwarder.start_forwarder()
    forwarder.link_layer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Heartbeat Nodes')
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str,
                        default='info', help='Logging Level (default: info)')
    args = parser.parse_args()
    main(args)
