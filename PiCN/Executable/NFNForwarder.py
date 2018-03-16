"""NFN Forwarder executable"""

import logging
import sys

import PiCN.ProgramLibs.NFNForwarder


def main(argv):

    port = 9000
    try:
        port = int(argv[1])
    except Exception:
        port = 9000

    forwarder = PiCN.ProgramLibs.NFNForwarder.NFNForwarder(port, logging.DEBUG)
    forwarder.start_forwarder()

    forwarder.linklayer.process.join()



if __name__ == "__main__":
    main(sys.argv)
