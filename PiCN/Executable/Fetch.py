"""
Fetch Content with resolved chunking
"""

import argparse

from PiCN.Packets import Name
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder


def main(args):
    name = Name(args.name)
    name.format = args.format

    encoder = NdnTlvEncoder() if args.format == 'ndntlv' else SimpleStringEncoder
    fetchTool = Fetch(args.ip, args.port, encoder=encoder)

    content = fetchTool.fetch_data(name)
    print(content)

    fetchTool.stop_fetch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ICN Fetch Tool')
    parser.add_argument('--format', choices=['ndntlv', ' simple'], type=str,
                        default='ndntlv', help='default is: "ndntlv"')
    parser.add_argument('ip', type=str,
                        help="IP addr of forwarder")
    parser.add_argument('port', type=int,
                        help="UDP port of forwarder")
    parser.add_argument('name', type=str,
                        help="ICN name of content to fetch")
    args = parser.parse_args()

    main(args)