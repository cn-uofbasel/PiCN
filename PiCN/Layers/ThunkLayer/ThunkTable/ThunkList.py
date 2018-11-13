"""An List Based implementation of the Thunk Table"""


from typing import List

from PiCN.Packets import Name

from PiCN.Layers.ThunkLayer.ThunkTable import BaseThunkTable, ThunkTableEntry

class ThunkList(BaseThunkTable):

    def __init__(self):
        super().__init__()

    def add_entry_to_thunk_table(self, name: Name, id: id, awaiting_data: List[Name]=None):
        """Add a new entry to the thunktable"""
        self.container.append(ThunkTableEntry(name, id, awaiting_data))

    def get_entry_from_name(self, name: Name) -> ThunkTableEntry:
        """Get an entry given the name"""
        for e in self.container:
            if e.name == name:
                return e

    def get_entry_from_id(self, id: int):
        """Get an entry given the id"""
        for e in self.container:
            if e.id == id:
                return e

    def add_awaiting_data(self, name: Name, awaiting_name: Name):
        """Add awaiting data to an entry in the Thunk Table"""
        for e in self.container:
            if e.name == name:
                e.awaiting_data[awaiting_name] = None
                return

    def add_estimated_cost_to_awaiting_data(self, name: Name, cost: int):
        """Add cost to an entry, if cost are lower than existing"""
        container_new = []
        for e in self.container:
            if name in e.awaiting_data:
                if e.awaiting_data.get(name) is None or e.awaiting_data.get(name) > cost:
                    e.awaiting_data[name] = cost
            container_new.append(e)
        self.container = container_new

    def remove_entry_from_thunk_table(self, name: Name):
        """Remove entry from the thunktable"""
        entry = self.get_entry_from_name(name)
        self.container.remove(entry)

    def remove_awaiting_data(self, awaiting_name: Name):
        """Removes awaiting data name from all """
        for e in self.container:
            if awaiting_name in e.awaiting_data:
                del e.awaiting_data[awaiting_name]