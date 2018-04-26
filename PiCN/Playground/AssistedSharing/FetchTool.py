""" Fetch Tool """

import argparse

from PiCN.Packets import Name
from PiCN.Playground.AssistedSharing.FetchStack import FetchStack


def main(args):
    # create stack
    fetchTool = FetchStack(args.ip, args.port, Name(args.name))

    # Note: fetching is triggered in FetchStack

    # stop
    # fetchTool.stop_fetch()
    # TODO - shift this into FetchStack?


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch Tool (assisted sharing)')
    parser.add_argument('ip', type=str,
                        help="IP addr of entry node")
    parser.add_argument('port', type=int,
                        help="UDP port of entry node")
    parser.add_argument('name', type=str,
                        help="ICN name of high-level object to fetch")
    args = parser.parse_args()

    main(args)
