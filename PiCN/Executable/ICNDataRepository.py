#!/usr/bin/env python3

"""ICN Data Repository executable"""

import argparse
import logging

from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.Packets import Name

# ----------------------------------------------------------------------

def main(args):

    prefix = Name(args.icnprefix)
    prefix.suite = args.suite
    repo = ICNDataRepository(args.repotype, args.datapath, prefix,
                             args.port, logging.DEBUG)
    repo.start_repo()

    repo.linklayer.process.join()

# ----------------------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='ICN Data Repository')
    parser.add_argument('--repotype', default='flic',
                        choices=['simple', 'flic'])
    parser.add_argument('--suite', default='ndn2013', type=str)
    parser.add_argument('datapath', type=str,
                        help='filesystem path where the repo stores its data')
    parser.add_argument('icnprefix', type=str,
                        help='prefix for all content stored in this repo')
    parser.add_argument('port', type=int, default=9000,
                        help="the repo's UDP and TCP port")

    args = parser.parse_args()
    main(args)

# eof
