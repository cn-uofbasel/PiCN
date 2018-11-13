"""The Plan Table maintains available plans e.g. """

from PiCN.Packets import Name
from typing import List, Dict


class PlanTable(object):
    """The Plan Table maintains available plans e.g. """

    def __init__(self):
        self.container: Dict[Name, (List[Name], int)] = {}

    def add_plan(self, name: Name, requests: List[Name], cost: int):
        if self.container.get(name) is not None:
            return
        self.container[name] = (requests, cost)

    def get_plan(self, name: Name) -> List[Name]:
        self.container.get(name)[0]

    def get_cost(self, name: Name) -> int:
        self.container.get(name)[1]