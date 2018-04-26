""" Fetch Tool """

import argparse

from PiCN.Packets import Name
from PiCN.Playground.AssistedSharing.FetchStack import FetchStack


def main(args):
    # create stack
    fetchTool = FetchStack(args.ip, args.port, Name(args.name))

    # fetch high-level object
    # content = fetchTool.fetch_data(Name(args.name))  # TODO

    # stop
    fetchTool.stop_fetch()


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
