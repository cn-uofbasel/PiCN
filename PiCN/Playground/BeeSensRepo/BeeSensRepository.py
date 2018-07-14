""" BeeSens Repository """

import argparse
import logging

import PiCN.Playground.BeeSensRepo.RepoStack
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
    logger.info("Starting a BeeSens Repo...")
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Web Port:       " + str(args.web_port))
    logger.info("Database Path:  " + str(args.database_path))
    logger.info("Empty Database: " + str(args.flush_database))
    logger.info("PEM Path:       " + str(args.pem_path))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  " + args.format)

    # Packet encoder
    encoder = NdnTlvEncoder(log_level) if args.format == 'ndntlv' else SimpleStringEncoder

    # Start
    forwarder = PiCN.Playground.BeeSensRepo.RepoStack(args.port, http_port=args.web_port, log_level=log_level,
                                                      encoder=encoder, database_path=args.database_path,
                                                      flush_database=args.flush_database, pem_path=args.pem_path)
    forwarder.start_forwarder()
    forwarder.link_layer.process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='BeeSens Repo')
    parser.add_argument('-p', '--port', type=int, default=9500,
                        help="UDP port (default: 9500)")
    parser.add_argument('-w', '--web-port', type=int, default=8080,
                        help="Port of REST Interface (default: 8080)")
    parser.add_argument('-d', '--database-path', default="/tmp",
                        help="Filesystem path of persistent database (default: /tmp)")
    parser.add_argument('--flush-database', action="store_true", help="Delete all entries from database")
    parser.add_argument('-k', '--pem-path', required=False,
                        help="Filesystem path of SSL pem file (http-only if not specified)")
    parser.add_argument('-f', '--format', choices=['ndntlv', 'simple'], type=str, default='ndntlv',
                        help='Packet Format (default: ndntlv)')
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str,
                        default='info', help='Logging Level (default: info)')
    args = parser.parse_args()
    main(args)
