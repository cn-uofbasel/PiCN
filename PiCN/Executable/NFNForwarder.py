"""NFN Forwarder executable"""

import asyncio
import logging
import argparse

import PiCN.ProgramLibs.NFNForwarder
from PiCN.Executable.Helpers.async_runtime import run_until_signal
from PiCN.Logger import Logger
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer, MapReduceOptimizer, EagerOptimizer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
from PiCN.ProgramLibs.runtime import Runtime

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
    logger = Logger("NFNForwarder", log_level)

    # Info
    logger.info("Starting a NFN Forwarder...")
    logger.info("UDP Port:       " + str(args.port))
    logger.info("Log Level:      " + args.logging)
    logger.info("Packet Format:  " + args.format)
    logger.info("Runtime:        " + args.runtime)

    # Packet encoder
    encoder = NdnTlvEncoder(log_level) if args.format == 'ndntlv' else SimpleStringEncoder(log_level)
    runtime = Runtime(args.runtime)

    if args.optimizer == "Edge":
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(
            args.port, log_level, encoder, ageing_interval=1, runtime=runtime)
        logger.info("Edge Computing Node")
        forwarder.icnlayer.pit.set_pit_timeout(2)
        forwarder.icnlayer.cs.set_cs_timeout(30)
        forwarder.nfnlayer.optimizer = EdgeComputingOptimizer(forwarder.icnlayer.cs, forwarder.icnlayer.fib,
                                                              forwarder.icnlayer.pit, forwarder.linklayer.faceidtable)
    elif args.optimizer == "Eager":
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(
            args.port, log_level, encoder, runtime=runtime)
        logger.info("Using Eager Optimizer")
        forwarder.nfnlayer.optimizer = EagerOptimizer(forwarder.icnlayer.cs, forwarder.icnlayer.fib,
                                                              forwarder.icnlayer.pit, forwarder.linklayer.faceidtable)
    elif args.optimizer == "MapReduce":
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(
            args.port, log_level, encoder, runtime=runtime)
        logger.info("Using MapReduce Optimizer")
        forwarder.nfnlayer.optimizer = MapReduceOptimizer(forwarder.icnlayer.cs, forwarder.icnlayer.fib,
                                                              forwarder.icnlayer.pit, forwarder.linklayer.faceidtable)
    elif args.optimizer == "Thunks":
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(
            args.port, log_level, encoder, use_thunks=True, runtime=runtime)
        logger.info("Using Thunks for Planning and Optimizing")
    else:
        forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(
            args.port, log_level, encoder, runtime=runtime)

    if runtime is Runtime.ASYNC:
        asyncio.run(run_until_signal(
            forwarder.start_forwarder_async, forwarder.stop_forwarder_async))
    else:
        forwarder.start_forwarder()
        forwarder.linklayer.process.join()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Forwarder')
    parser.add_argument('-p', '--port', type=int, default=9000, help="UDP port (default: 9000)")
    parser.add_argument('-f', '--format', choices=['ndntlv','simple'], type=str, default='ndntlv', help='Packet Format (default: ndntlv)')
    parser.add_argument('-l', '--logging', choices=['debug','info', 'warning', 'error', 'none'], type=str, default='info', help='Logging Level (default: info)')
    parser.add_argument('-e', '--optimizer', choices=['ToDataFirst', 'Edge', 'Eager', 'MapReduce', 'Thunks'], type=str, default="ToDataFirst", help="Choose the NFN Optimizer")
    parser.add_argument('--runtime', choices=['sync', 'async'], type=str, default='sync',
                        help='Execution runtime (default: sync)')
    args = parser.parse_args()
    main(args)
