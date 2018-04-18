"""Implementation of the NFNComputationTable using a list"""

import time

from PiCN.Layers.NFNLayer.NFNComputationTable.BaseNFNComputationTable import BaseNFNComputationTable, NFNComputationTableEntry
from PiCN.Layers.NFNLayer.R2C import BaseR2CClient

class NFNComputationList(BaseNFNComputationTable):
    """Implementation of the NFNComputationTable using a list"""

    def __init__(self, r2cclient: BaseR2CClient):
        super().__init__(r2cclient)


    def add_computation(self, name):
        if self.is_comp_running(name):
            return
        self.container.append(NFNComputationTableEntry(name, self.r2cclient))

    def is_comp_running(self, name):
        l = list(map(lambda n: n.original_name, self.container))
        if name in list(map(lambda n: n.original_name, self.container)):
            return True
        else:
            return False

    def push_data(self, content):
        for s in self.container:
            s.push_data(content)

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
        return requests
