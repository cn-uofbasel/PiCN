"""NFN Forwarder executable"""

import logging
import sys
import argparse

import PiCN.ProgramLibs.NFNForwarder
from PiCN.Logger import Logger
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer, MapReduceOptimizer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
import os


def main(argv):

    # correct missing / in keylocation input
    if type(args.keylocation) != type(None):
        if args.keylocation[-1:] != '/':
            args.keylocation += '/'


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
    logger = Logger("NFNForwarder", log_level)

    # Info
    logger.info("Starting a NFN Forwarder...")
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  " + args.format)

    # Packet encoder
    encoder = NdnTlvEncoder(log_level,file_location=args.keylocation, myname=args.name) if args.format == 'ndntlv' else SimpleStringEncoder(log_level)


    if args.optimizer == "Edge":
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(args.port, log_level, encoder, ageing_interval=1)
        logger.info("Edge Computing Node")
        forwarder.icnlayer.pit.set_pit_timeout(2)
        forwarder.icnlayer.cs.set_cs_timeout(30)
        forwarder.nfnlayer.optimizer = EdgeComputingOptimizer(forwarder.icnlayer.cs, forwarder.icnlayer.fib,
                                                              forwarder.icnlayer.pit, forwarder.linklayer.faceidtable)
    elif args.optimizer == "MapReduce":
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(args.port, log_level, encoder)
        logger.info("Using MapReduce Optimizer")
        forwarder.nfnlayer.optimizer = MapReduceOptimizer(forwarder.icnlayer.cs, forwarder.icnlayer.fib,
                                                              forwarder.icnlayer.pit, forwarder.linklayer.faceidtable)
    elif args.optimizer == "Thunks":
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(args.port, log_level, encoder, use_thunks=True)
        logger.info("Using Thunks for Planning and Optimizing")
    else:
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(args.port, log_level, encoder, corrupted=args.corrupted)

    forwarder.start_forwarder()

    forwarder.linklayer.process.join()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Forwarder')
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-f', '--format', choices=['ndntlv','simple'], type=str, default='ndntlv', help='Packet Format (default: ndntlv)')
    parser.add_argument('-l', '--logging', choices=['debug','info', 'warning', 'error', 'none'], type=str, default='info', help='Logging Level (default: info)')
    parser.add_argument('-e', '--optimizer', choices=['ToDataFirst', 'Edge', 'MapReduce', 'Thunks'], type=str, default="ToDataFirst", help="Choose the NFN Optimizer")
    parser.add_argument('-k', '--keylocation', type=str, help="Location of the key files (default: ~PiCN/identity/)",
                        default="~/PiCN/identity/")
    parser.add_argument('-c','--corrupted', choices=[False, True], type=bool,
                        default=False, help='default is: "False"')
    parser.add_argument('-n', '--name', type=str, help="name of this node, used as prefix (default: None)",
                        default=None)

    args = parser.parse_args()
    main(args)
