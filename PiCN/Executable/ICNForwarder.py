"""ICN Forwarder executable"""

import argparse
import logging

import PiCN.ProgramLibs.ICNForwarder
from PiCN.Executable.Helpers.ConfigParser import ConfigParser
import PiCN.Executable.Helpers.ConfigParser.CouldNotOpenConfigError
import PiCN.Executable.Helpers.ConfigParser.CouldNotParseError
import PiCN.Executable.Helpers.ConfigParser.MalformedConfigurationError
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
    logger = Logger("ICNForwarder", log_level)

    # Config file
    if args.config:
        try:
            conf = ConfigParser(args.config)
        except CouldNotOpenConfigError:
            pass



    # Info
    logger.info("Starting a CCN Forwarder...")
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  " + args.format)

    # Packet encoder
    encoder = NdnTlvEncoder(log_level) if args.format == 'ndntlv' else SimpleStringEncoder

    # Start
    forwarder = PiCN.ProgramLibs.ICNForwarder.ICNForwarder(args.port, log_level, encoder, autoconfig=args.autoconfig)
    forwarder.start_forwarder()
    forwarder.linklayer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Forwarder')
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-f', '--format', choices=['ndntlv','simple'], type=str, default='ndntlv', help='Packet Format (default: ndntlv)')
    parser.add_argument('-c', '--config', type=str, default=None, help="Path to configuration file")
    parser.add_argument('-a', '--autoconfig', action='store_true', help='Enable autoconfig server')
    parser.add_argument('-l', '--logging', choices=['debug','info', 'warning', 'error', 'none'], type=str, default='info', help='Logging Level (default: info)')
    args = parser.parse_args()
    main(args)
