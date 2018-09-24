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
    name = unescape_name(name)

    encoder = NdnTlvEncoder() if args.format == 'ndntlv' else SimpleStringEncoder
    fetchTool = Fetch(args.ip, args.port, encoder=encoder, autoconfig=args.autoconfig)

    content = fetchTool.fetch_data(name)
    print(content)

    fetchTool.stop_fetch()

def unescape_name(name):
    r = []
    for n in range(0, len(name.string_components)):
        r.append(name.string_components[n].replace("%2F", "/"))
    name.string_components = r
    return name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ICN Fetch Tool')
    parser.add_argument('--format', choices=['ndntlv', ' simple'], type=str,
                        default='ndntlv', help='default is: "ndntlv"')
    parser.add_argument('-a', '--autoconfig', action='store_true')
    parser.add_argument('ip', type=str,
                        help="IP addr of forwarder")
    parser.add_argument('port', type=int,
                        help="UDP port of forwarder")
    parser.add_argument('name', type=str,
                        help="ICN name of content to fetch")
    args = parser.parse_args()

    main(args)
