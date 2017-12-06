"""ICN Forwarder executable"""

import logging
import sys

import PiCN.ProgramLibs.ICNForwarder


def main(argv):


    port = 9000
    try:
        port = int(argv[1])
    except Exception:
        port = 9000

    forwarder = PiCN.ProgramLibs.ICNForwarder.ICNForwarder(port, logging.DEBUG)
    forwarder.start_forwarder()

    forwarder.linklayer.process.join()


if __name__ == "__main__":
    main(sys.argv)