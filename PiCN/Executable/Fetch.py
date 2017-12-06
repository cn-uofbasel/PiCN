"""Tool to Fetch Content, demonstrates how a application can use the stack"""

import sys

from PiCN.Packets import Name
from PiCN.ProgramLibs.Fetch import Fetch


def main(argv):
    if len(argv) != 4:
        print("usage: ", argv[0], "ip, port, name")
        return

    #parameter
    ip = argv[1]
    port = int(argv[2])
    name = argv[3]
    fetchTool = Fetch(ip, port)
    content = fetchTool.fetch_data(Name(name))

    print(content)
    
    fetchTool.stop_fetch()

if __name__ == "__main__":
    main(sys.argv)