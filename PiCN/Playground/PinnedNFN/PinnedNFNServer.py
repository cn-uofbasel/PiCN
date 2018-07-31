""" PinnedNFNServer Repository """

import argparse
import logging

import PiCN.Playground.PinnedNFN.PinnedNFNStack
from PiCN.Logger import Logger
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder


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
    logger.info("Starting a Two-Phase Computation Server...")
    logger.info("Replica ID:     " + str(args.id))
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  " + args.format)

    # Packet encoder
    encoder = NdnTlvEncoder(log_level) if args.format == 'ndntlv' else SimpleStringEncoder

    # Start
    server = PiCN.Playground.PinnedNFN.PinnedNFNStack(replica_id=args.id, port=args.port, log_level=log_level,
                                                      encoder=encoder)
    server.start_forwarder()
    server.link_layer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Two-Phase NFN Server')
    parser.add_argument('-i', '--id', type=int, help="ID of this replica", default=1)
    # parser.add_argument('-i', '--id', type=int, help="ID of this replica", required=True)
    parser.add_argument('-p', '--port', type=int, default=3000,
                        help="UDP port (default: 3000)")
    parser.add_argument('-f', '--format', choices=['ndntlv', 'simple'], type=str, default='ndntlv',
                        help='Packet Format (default: ndntlv)')
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str,
                        default='info', help='Logging Level (default: info)')
    args = parser.parse_args()
    main(args)
