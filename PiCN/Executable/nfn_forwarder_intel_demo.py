"""NFN Forwarder executable"""

import logging
import sys
import argparse
import time

import PiCN.ProgramLibs.NFNForwarder
from PiCN.Logger import Logger
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer, MapReduceOptimizer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Packets import *

def main(argv):

    # Log Level
    log_level = logging.DEBUG

    # Packet encoder
    encoder = NdnTlvEncoder(log_level)
    forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(0, log_level, encoder)
    forwarder.start_forwarder()

    time.sleep(1)

    add_info1 = AddressInfo(("127.0.0.1", 9100), 0)
    fid1 = forwarder.linklayer.faceidtable.get_or_create_faceid(add_info1)
    forwarder.icnlayer.fib.add_fib_entry(Name("/ndn/ch/unibas/nfn/dat"), [fid1], True)

    add_info2 = AddressInfo(("127.0.0.1", 9200), 0)
    fid2 = forwarder.linklayer.faceidtable.get_or_create_faceid(add_info2)
    forwarder.icnlayer.fib.add_fib_entry(Name("/ndn/ch/unibas/nfn/fct"), [fid2], True)

if __name__ == "__main__":
    main(sys.argv)

