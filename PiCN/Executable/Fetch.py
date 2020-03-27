"""
Fetch Content with resolved chunking
"""

import argparse

from PiCN.Packets import Name
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer

def main(args):
    name_str = args.name
    name = None
    if 'NFN' in name_str and '_' not in name_str:
        name = parse_nfn_str(name_str)

    if name is None:
        if '[' in name_str and ']' in name_str:
            name = unescape_str_to_Name(args.name)
        else:
            name = Name(args.name)
            name = unescape_name(name)
    name.format = args.format

    encoder = NdnTlvEncoder() if args.format == 'ndntlv' else SimpleStringEncoder
    fetchTool = Fetch(args.ip, args.port, encoder=encoder, autoconfig=args.autoconfig)

    content = fetchTool.fetch_data(name, timeout=10)


    print(content)

    fetchTool.stop_fetch()

    #print(type(content))
    if content is '7':
        print("content object saved to " + "~PiCN/demo/" + 'contetntobject.corrupted')
    if content is '3':
        print("content object saved to " + "~PiCN/demo/" + 'contetntobject')


def unescape_name(name: Name):
    r = []
    for n in range(0, len(name.string_components)):
        r.append(name.string_components[n].replace("%2F", "/"))
    name.string_components = r
    return name

def unescape_str_to_Name(name: str) -> Name:
    r = []
    if '[' not in name or ']' not in name:
        return Name(name)
    tmp_comps1 = name.split('[')
    tmp_comps2 = tmp_comps1[1].split(']')
    if tmp_comps1[0].endswith("/"):
        tmp_comps1[0] = tmp_comps1[0][:-1]
    if tmp_comps2[1].startswith("/"):
        tmp_comps2[1] = tmp_comps2[1][1:]
    comps = [tmp_comps1[0], tmp_comps2[0], tmp_comps2[1]]

    name = Name(comps[0])
    name += comps[1]
    name += comps[2]

    return name

def parse_nfn_str(name: str) -> Name:
    name = name.replace("""'""", "")
    parser = DefaultNFNParser()
    optimizer = BaseNFNOptimizer(None, None, None, None)
    if '/NFN' in name:
        name = name.replace("/NFN", "")
    ast = parser.parse(name)
    if ast is None:
        return None
    names = optimizer._get_names_from_ast(ast)
    if names is None or names == []:
        names = optimizer._get_functions_from_ast(ast)
    if names is None or names == []:
        return None
    prepend_name = Name(names[0])
    if prepend_name is None:
        return None
    name_str = optimizer._set_prepended_name(ast, prepend_name, ast)
    if name_str is None:
        return None
    res = parser.nfn_str_to_network_name(name_str)
    return res


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
    parser.add_argument('-s', '--filelocation' , type=str, default='~PICN/save')
    args = parser.parse_args()


    main(args)
