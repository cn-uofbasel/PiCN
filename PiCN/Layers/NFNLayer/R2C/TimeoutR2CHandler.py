"""Implementation of an Simple R2CClient"""

from typing import List

from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.R2C import BaseR2CHandler
from PiCN.Packets import Name, Content


class TimeoutR2CHandler(BaseR2CHandler):
    def __init__(self, parser: DefaultNFNParser = DefaultNFNParser()):
        super().__init__(parser)

    def R2C_selection(self, names: List[Name]) -> List[Name]:
        return_list = []
        for n in names:
            if b"R2C" in n.components:
                continue
            if n.components[-1] == b"NFN":
                return_list.append(n)
            else:
                return None
        return return_list

    def R2C_handle_reply(self, name: Name):
        pass

    def R2C_create_message(self, name: Name):
        if type(name) is str:
            name = self.parser.nfn_str_to_network_name(name)
        new_name = Name(name.components[:])
        new_name.components.remove(b"NFN")
        new_name.components.append(b"R2C")
        new_name.components.append(b"KEEPALIVE")
        new_name.components.append(b"NFN")
        return new_name

    def R2C_get_original_message(self, name: Name):
        if type(name) is str:
            name = self.parser.nfn_str_to_network_name(name)
        new_name = Name(name.components[:])
        new_name.components.remove(b"R2C")
        new_name.components.remove(b"KEEPALIVE")
        return new_name

    def R2C_identify_Name(self, name: Name):
        if type(name) is str:
            name = self.parser.nfn_str_to_network_name(name)
        if len(name.components) < 3:
            return False
        return name.components[-1] == b"NFN" and name.components[-2] == b"KEEPALIVE" and name.components[-3] == b"R2C"

    def R2C_handle_request(self, name: Name, computationTable: BaseNFNComputationTable):
        n = self.R2C_get_original_message(name)
        if computationTable.get_computation(n) is not None:
            return Content(name, "Running")
        return None
