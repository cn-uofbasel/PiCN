"""ICN Forwarder executable"""

import argparse
import logging
import datetime

import PiCN.ProgramLibs.ICNForwarder
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
    else:
        log_level = logging.DEBUG
    logger = Logger("ICNForwarder", log_level)

    # Info
    logger.info("Starting a CCN Forwarder...")
    logger.info("UDP Port:    " + str(args.port))
    logger.info("Log Level:   " + args.logging)
    logger.info("Wire Format: " + args.suite)

    # Packet encoder
    encoder = NdnTlvEncoder() if args.suite == 'ndntlv' else SimpleStringEncoder

    # Start
    forwarder = PiCN.ProgramLibs.ICNForwarder.ICNForwarder(args.port, log_level, encoder)
    forwarder.start_forwarder()
    forwarder.linklayer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CCN Forwarder')
    parser.add_argument('port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('--suite', choices=['ndntlv','simple'], type=str, default='ndntlv', help='default is: "ndntlv"')
    parser.add_argument('--logging', choices=['debug','info', 'warning', 'error'], type=str, default='info', help='default is: "debug"')
    args = parser.parse_args()
    main(args)