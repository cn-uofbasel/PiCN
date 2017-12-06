"""MGMT Tool for sending MGMT requests"""

import sys
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name

def main(argv):


    if len(argv) < 3:
        error()
        return
    port = int(argv[1])
    command = argv[2]

    mgmt_client = MgmtClient(port)

    if command == "shutdown":
        mgmt_client.shutdown()
        return
    if len(argv) != 4:
        error()
        return

    param: str = argv[3]
    data = "error"
    if command == "newface":
        data = mgmt_client.add_face(param.split(":")[0], param.split(":")[1])
    elif command == "newforwardingrule":
        data = mgmt_client.add_forwarding_rule(Name(param.split(":")[0]), param.split(":")[1])
    elif command == "newcontent":
        data = mgmt_client.add_new_content(Name(param.split(":")[0]), param.split(":")[1])
    if data == "error":
        error()
        return
    print(data)

def error():
    print("usage:", sys.argv[0], "port command [param]")
    print("\tcommands:")
    print("\t\tshutdown")
    print("\t\tnewface ip:port")
    print("\t\tnewforwardingrule prefix:face")
    print("\t\tnewcontent name:content")

if __name__ == "__main__":
    main(sys.argv)