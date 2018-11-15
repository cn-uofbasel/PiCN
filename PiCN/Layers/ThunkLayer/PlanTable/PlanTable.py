"""The Plan Table maintains available plans e.g. """

from PiCN.Packets import Name
from typing import List, Dict
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser


class PlanTable(object):
    """The Plan Table maintains available plans e.g. """

    def __init__(self, parser: DefaultNFNParser):
        self.container: Dict[Name, (List[Name], int)] = {}
        self.parser = parser

    def add_plan(self, name: Name, requests: List[Name], cost: int):
        if self.container.get(name) is not None:
            return
        self.container[name] = (requests, cost)

    def get_plan(self, name: Name) -> List[Name]:
        res = self.container.get(name)
        if res is None:
            return None
        return res[0]

    def get_cost(self, name: Name) -> int:
        res = self.container.get(name)
        if res is None:
            return None
        return res[1]

    def get_container(self):
        return self.container

    def compute_fwd(self, name: Name):
        """checks if plan size is 1 (FWD) or if subcomp that should be forwarded"""
        plan = self.get_plan(name)
        if plan == None:
            for e in self.container: #check for subcomp
                entry_names = self.container.get(e)[0]
                entry_names_str = list(map(lambda x: self.parser.network_name_to_nfn_str(x)[0],entry_names))
                name_str = self.parser.network_name_to_nfn_str(name)[0]
                if name_str in entry_names_str:
                    return True
            return False
        elif len(plan) == 1:
            return True
        return False

    def rewirte(self, name) -> Name:
        """check if there is a rewrite for a plan available, or for rewrite of subcomputation"""
        plan = self.get_plan(name)
        if plan is not None:
            if len(plan) != 1:
                return None
            else:
                return plan[0]
        for e in self.container:
            entry_names = self.container.get(e)[0]
            if len(entry_names) == 1:
                n1 = self.parser.network_name_to_nfn_str(entry_names[0])
                n2 = self.parser.network_name_to_nfn_str(name)
                if n1 == n2:
                    return entry_names[0]
        return None


