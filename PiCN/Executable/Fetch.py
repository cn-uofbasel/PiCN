#!/usr/bin/env python3

"""Tool to Fetch Content, demonstrates how a application can use the stack"""

import argparse

from PiCN.Packets import Name
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder

# ---------------------------------------------------------------------------

def main(args):

    name = Name(args.name)
    name.suite = args.suite

    encoder = NdnTlvEncoder() if args.suite == 'ndn2013' else None
    fetchTool = Fetch(args.ip, args.port, encoder = encoder)

    content = fetchTool.fetch_data(name)
    print(content)
    
    fetchTool.stop_fetch()

# ---------------------------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='ICN Fetch Tool')
    parser.add_argument('--suite', choices=['ndn2013',' simple'], type=str,
                        default='ndn2013', help='default is: "ndn2013"')
    parser.add_argument('ip',   type=str,
                        help="IP addr of forwarder")
    parser.add_argument('port', type=int,
                        help="UDP port of forwarder")
    parser.add_argument('name', type=str,
                        help="ICN name of content to fetch")
    args = parser.parse_args()

    main(args)

# eof
