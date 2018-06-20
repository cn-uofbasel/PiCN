"""Implementation of the NFNComputationTable using a list"""

import time


from PiCN.Packets import Name, Interest
from PiCN.Layers.NFNLayer.NFNComputationTable.BaseNFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.NFNComputationTable.BaseNFNComputationTable import NFNComputationTableEntry
from PiCN.Layers.NFNLayer.NFNComputationTable.BaseNFNComputationTable import NFNComputationState
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.NFNLayer.R2C import BaseR2CHandler

class NFNComputationList(BaseNFNComputationTable):
    """Implementation of the NFNComputationTable using a list"""

    def __init__(self, r2cclient: BaseR2CHandler, parser: DefaultNFNParser):
        super().__init__(r2cclient, parser)


    def add_computation(self, name: Name, id: int, interest, ast:AST=None) -> bool:
        if self.is_comp_running(name):
            c = self.get_computation(name)
            c.time_stamp = time.time()
            return False
        self.container.append(NFNComputationTableEntry(name, id, interest, ast, self.r2cclient, self.parser))
        return True

    def is_comp_running(self, name):
        l = list(map(lambda n: n.original_name, self.container))
        if name in list(map(lambda n: n.original_name, self.container)):
            return True
        else:
            return False

    def push_data(self, content):
        ret = False
        for s in self.container:
            v = s.push_data(content)
            if v is True:
                ret = True
        return ret

    def get_computation(self, name: Name):
        for c in self.container:
            if name == c.original_name:
                return c
        return None

    def remove_computation(self, name: Name):
        c = self.get_computation(name)
        if c is not None:
            self.container.remove(c)

    def append_computation(self, entry: NFNComputationTableEntry):
        if entry not in self.container:
            self.container.append(entry)

    def get_ready_computations(self):
        return list(filter(lambda n: n.ready_to_continue() == True, self.container))

    def ageing(self):
        comp_to_remove = []
        requests = []
        for comp in self.container:
            required_requests = comp.ageing()
            if required_requests == []:
                continue
            if required_requests == None:
                comp_to_remove.append(comp) #remove comp if there was a timeout that should not be refreshed
            else:
                requests += required_requests
        for c in comp_to_remove:
            self.container.remove(c)
        return (requests, list(map(lambda n: n.original_name, comp_to_remove)))
