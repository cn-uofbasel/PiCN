"""NFN Forwarder executable"""

import logging
import sys

import PiCN.ProgramLibs.NFNForwarder
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer


def main(argv):
    port = 9000
    try:
        port = int(argv[1])
    except Exception:
        port = 9000

    forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(port, logging.DEBUG)

    if len(argv) == 3 and argv[2] == "EDGE":
        print("Edge Computing Node")
        forwarder.nfnlayer.optimizer = EdgeComputingOptimizer(forwarder.icnlayer.cs, forwarder.icnlayer.fib,
                                                              forwarder.icnlayer.pit)

    forwarder.start_forwarder()

    forwarder.linklayer.process.join()


if __name__ == "__main__":
    main(sys.argv)
