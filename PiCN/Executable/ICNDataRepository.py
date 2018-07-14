"""ICN Data Repository executable"""

import argparse
import logging

from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.Packets import Name
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder


def main(args):

    prefix = Name(args.icnprefix)

    log_level = logging.DEBUG

    if args.format == "ndntlv":
        encoder = NdnTlvEncoder()
    else:
        encoder = SimpleStringEncoder(log_level=log_level)

    repo = ICNDataRepository(args.datapath, prefix,
                             args.port, log_level, encoder=encoder)
    repo.start_repo()

    repo.linklayer.process.join()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='ICN Data Repository')
    parser.add_argument('--format', default='ndntlv', type=str)
    parser.add_argument('datapath', type=str,
                        help='filesystem path where the repo stores its data')
    parser.add_argument('icnprefix', type=str,
                        help='prefix for all content stored in this repo')
    parser.add_argument('port', type=int, default=9000,
                        help="the repo's UDP and TCP port (TCP only for MGMT)")

    args = parser.parse_args()
    main(args)
