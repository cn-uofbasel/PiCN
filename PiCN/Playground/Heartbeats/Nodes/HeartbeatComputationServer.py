""" Heartbeat Computation Server """

import argparse
import logging

import PiCN.Playground.Heartbeats.Nodes.HeartbeatForwarderStack
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
    logger = Logger("Repo", log_level)

    # Info
    logger.info("Starting a PinnedNFN Server...")
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  Extended NDN Packet Format")

    # Packet encoder
    encoder = ExtendedNdnTlvEncoder(log_level)

    # Start
    server = PiCN.Playground.Heartbeats.Nodes.HeartbeatForwarderStack(port=args.port, log_level=log_level, encoder=encoder)
    server.start_forwarder()
    server.link_layer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Heartbeat NFN Server')
    parser.add_argument('-p', '--port', type=int, default=3000,
                        help="UDP port (default: 3000)")
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str,
                        default='info', help='Logging Level (default: info)')
    args = parser.parse_args()
    main(args)
