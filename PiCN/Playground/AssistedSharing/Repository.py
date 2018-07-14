""" Assisted Sharing Repository """

import argparse
import logging

import PiCN.Playground.AssistedSharing.RepoStack
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
from PiCN.Logger import Logger


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
    logger.info("Starting a Repo...")
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  " + args.format)

    # Packet encoder
    encoder = NdnTlvEncoder(log_level) if args.format == 'ndntlv' else SimpleStringEncoder

    # Start
    forwarder = PiCN.Playground.AssistedSharing.RepoStack(args.port, log_level, encoder)
    forwarder.start_forwarder()
    forwarder.link_layer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Assisted Sharing Repo')
    parser.add_argument('-p', '--port', type=int, default=8500,
                        help="UDP port (default: 8500)")  # TODO -- choose a port
    parser.add_argument('-f', '--format', choices=['ndntlv', 'simple'], type=str, default='ndntlv',
                        help='Packet Format (default: ndntlv)')
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str,
                        default='info', help='Logging Level (default: info)')
    args = parser.parse_args()
    main(args)
