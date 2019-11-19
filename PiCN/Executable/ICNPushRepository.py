"""ICN Push Repository executable"""

import argparse
import logging

import PiCN.ProgramLibs.ICNPushRepository
from PiCN.Executable.Helpers.ConfigParser import ConfigParser
from PiCN.Executable.Helpers.ConfigParser.ConfigParser import CouldNotOpenConfigError, CouldNotParseError, MalformedConfigurationError
from PiCN.Logger import Logger
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder

# default arguments
default_port = 9100
default_format = "ndntlv"
default_logging = "info"


def main(args):
    logger = Logger("ICNPushRepo", logging.DEBUG)  # note: set later according to cli/config arguments
    logger.info("Starting a Push Repository...")

    # Parse Configuration file
    conf = None
    if args.config != "none":
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
            args.port = default_port

    if not args.format:
        if conf and conf.format:
            args.format = conf.format
        else:
            args.format = default_format

    if not args.logging:
        if conf and conf.logging:
            args.logging = conf.logging
        else:
            args.logging = default_logging

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
    logger.info("Database:       " + args.database_path)
    logger.info("Flush DB:       " + str(args.flush_database))

    # Packet encoder
    encoder = NdnTlvEncoder(log_level) if args.format == 'ndntlv' else SimpleStringEncoder(log_level)

    # Start
    forwarder = PiCN.ProgramLibs.ICNPushRepository.ICNPushRepository(args.database_path, args.port, log_level, encoder, args.flush_database)
    forwarder.start_forwarder()
    forwarder.linklayer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Push Repository')
    parser.add_argument('-p', '--port', type=int, default=None, help=f'UDP port (default: {default_port})')
    parser.add_argument('-f', '--format', choices=['ndntlv', 'simple'], type=str, default=None,
                        help=f'Packet Format (default: {default_format})')
    parser.add_argument('-c', '--config', type=str, default="none", help="Path to configuration file")
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str,
                        default=None, help=f'Logging Level (default: {default_logging})')
    parser.add_argument('-d', '--database-path', default="/tmp",
                        help="Filesystem path of persistent database (default: /tmp)")
    parser.add_argument('--flush-database', action="store_true", help="Delete all entries from database")

    args = parser.parse_args()
    main(args)
