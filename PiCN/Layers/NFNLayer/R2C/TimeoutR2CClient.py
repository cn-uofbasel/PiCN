"""Implementation of an Simple R2CClient"""

from typing import List

from PiCN.Layers.NFNLayer.R2C import BaseR2CClient
from PiCN.Packets import Name

class TimeoutR2CClient(BaseR2CClient):

    def R2C_selection(self, names: List[Name]) -> List[Name]:
        return_list = []
        for n in names:
            if n.components[-1] == b"NFN":
                return_list.append(n)
            else:
                return None
        return return_list

    def R2C_handle_reply(self, name: Name):
        pass

    def R2C_create_message(self, name: Name):
        new_name = Name(name.components)
        new_name.components.remove(b"NFN")
        new_name.components.append(b"R2C")
        new_name.components.append(b"KEEPALIVE")
        new_name.components.append(b"NFN")
        return new_name
