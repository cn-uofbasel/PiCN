"""ICN Data Repository executable"""

import logging
import sys

import PiCN.ProgramLibs.ICNDataRepository
from PiCN.Packets import Name


def main(argv):

    if len(argv) != 4:
        print("usage: ", argv[0], "datapath icnprefix port")
        return

    path = argv[1]
    icnprefix = Name(argv[2])

    port = 9000
    try:
        port = int(argv[3])
    except Exception:
        port = 9000

    repo = PiCN.ProgramLibs.ICNDataRepository.ICNDataRepository(path, icnprefix, port, logging.DEBUG)
    repo.start_repo()

    repo.linklayer.process.join()

if __name__ == "__main__":
    main(sys.argv)