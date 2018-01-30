"""ICN Forwarder executable"""

import logging
import sys

import PiCN.ProgramLibs.ICNForwarder
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder


def main(argv):


    port = 9000
    try:
        port = int(argv[1])
    except Exception:
        port = 9000

    try:
        if argv[2] == "ndntlv":
            encoder = NdnTlvEncoder()
        else:
            encoder = SimpleStringEncoder()
    except:
        encoder = SimpleStringEncoder()

    forwarder = PiCN.ProgramLibs.ICNForwarder.ICNForwarder(port, logging.DEBUG, encoder)
    forwarder.start_forwarder()

    forwarder.linklayer.process.join()


if __name__ == "__main__":
    main(sys.argv)