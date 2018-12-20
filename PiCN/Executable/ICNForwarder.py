"""ICN Forwarder executable"""

import argparse
import logging

import PiCN.ProgramLibs.ICNForwarder
from PiCN.Executable.Helpers.ConfigParser import ConfigParser
from PiCN.Executable.Helpers.ConfigParser.ConfigParser import CouldNotOpenConfigError, CouldNotParseError, MalformedConfigurationError
from PiCN.Logger import Logger
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder

# default arguments
default_port = 9000
default_format = "ndntlv"
default_logging = "info"

def main(args):
    logger = Logger("ICNForwarder", logging.DEBUG) # note: set later according to cli/config arguments
    logger.info("Starting a CCN Forwarder...")

    # Parse Configuration file
    conf = None
    if args.config:
        try:
            conf = ConfigParser(args.config)
            logger.info("Successfully parsed configuration file.")
        except CouldNotOpenConfigError:
            conf = None
            logger.warning("Could not open configuration file. Proceed with command line arguments or default values.")
        except CouldNotParseError:
            logger.warning("Could not parse configuration file. Proceed with command line arguments or default values.")
        except MalformedConfigurationError as e:
            logger.warning("Invalid configuration file. Proceed with command line arguments or default values. Hint: " + str(e))

    # Choose command line arguments before config file arguments before default values
    if not args.port:
        if conf and conf.udp_port:
            args.port = conf.udp_port
        else:
            args.port= default_port

    if not args.format:
        if conf and conf.format:
            args.format = conf.format
        else:
            args.format = default_format

    if not args.logging:
        if conf and conf.logging:
            args.logging = conf.logging
        else:
            args.logging= default_logging

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
    logger.setLevel(log_level)

    # Info
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  " + args.format)

    # Packet encoder
    encoder = NdnTlvEncoder(log_level) if args.format == 'ndntlv' else SimpleStringEncoder(log_level)

    # Start
    forwarder = PiCN.ProgramLibs.ICNForwarder.ICNForwarder(args.port, log_level, encoder, autoconfig=args.autoconfig)
    forwarder.start_forwarder()
    forwarder.linklayer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Forwarder')
    parser.add_argument('-p', '--port', type=int, default=None, help=f'UDP port (default: {default_port})')
    parser.add_argument('-f', '--format', choices=['ndntlv', 'simple'], type=str, default=None, help=f'Packet Format (default: {default_format})')
    parser.add_argument('-c', '--config', type=str, default=None, help="Path to configuration file")
    parser.add_argument('-a', '--autoconfig', action='store_true', help='Enable autoconfig server')
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str, default=None, help=f'Logging Level (default: {default_logging})')
    args = parser.parse_args()
    main(args)
