"""Implementation of the NFNComputationTable using a list"""

import time


from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.NFNComputationTable.BaseNFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.NFNComputationTable.BaseNFNComputationTable import NFNComputationTableEntry
from PiCN.Layers.NFNLayer.NFNComputationTable.BaseNFNComputationTable import NFNComputationState
from PiCN.Layers.NFNLayer.R2C import BaseR2CHandler

class NFNComputationList(BaseNFNComputationTable):
    """Implementation of the NFNComputationTable using a list"""

    def __init__(self, r2cclient: BaseR2CHandler):
        super().__init__(r2cclient)


    def add_computation(self, name, id, interest, ast=None):
        if self.is_comp_running(name):
            return
        self.container.append(NFNComputationTableEntry(name, id, interest, ast, self.r2cclient))

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
        self.container.remove(c)

    def append_computation(self, entry: NFNComputationTableEntry):
        if entry not in self.container:
            self.container.append(entry)

    def get_ready_computations(self):
        return list(filter(lambda n: n.ready_to_continue() == True, self.container))

    def ageing(self):  #TODO, what to do with NACKs for removed computations
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
