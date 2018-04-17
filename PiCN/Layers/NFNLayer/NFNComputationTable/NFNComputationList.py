"""Implementation of the NFNComputationTable using a list"""

from .BaseNFNComputationTable import BaseNFNComputationTable, NFNComputationTableEntry

class NFNComputationList(BaseNFNComputationTable):
    """Implementation of the NFNComputationTable using a list"""

    def __init__(self):
        super().__init__()

    def add_computation(self, name):
        if self.is_comp_running(name):
            return
        self.container.append(NFNComputationTableEntry(name))

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
