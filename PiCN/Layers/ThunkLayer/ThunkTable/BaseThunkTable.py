"""Base Class for the Thunk Table. A Thunk Table will maintain the status of the Thunk Requests"""

import abc
import time

from typing import List

from PiCN.Packets import Name

class ThunkTableEntry:
    """An Entry of the Thunk Table"""

    def __init__(self, name: Name, id: int, awaiting_data: List[Name]=None):
        self.ts = time.time()
        self.name = name
        self.id = id
        self.awaiting_data = {} #maps name -> cost.
        if awaiting_data is not None:
            for e in awaiting_data:
                self.awaiting_data[e] = None



class BaseThunkTable(object):
    """Base Class for the Thunk Table"""

    def __init__(self):
        self.container: List[ThunkTableEntry] = []

    @abc.abstractmethod
    def add_entry_to_thunk_table(self, name: Name, id: id, awaiting_data: List[Name]=None):
        """Add a new entry to the thunktable"""

    @abc.abstractmethod
    def get_entry_from_name(self, name: Name):
        """Get an entry given the name"""

    @abc.abstractmethod
    def get_entry_from_id(self, id: int):
        """Get an entry given the id"""

    @abc.abstractmethod
    def add_awaiting_data(self, name: Name, awaiting_name: Name):
        """Add awaiting data to an entry in the Thunk Table"""

    @abc.abstractmethod
    def add_estimated_cost_to_awaiting_data(self, name: Name, cost: int):
        """Add cost to an entry, if cost are lower than existing"""

    @abc.abstractmethod
    def remove_entry_from_thunk_table(self, name: Name):
        """Remove entry from the thunktable"""

    @abc.abstractmethod
    def remove_awaiting_data(self, awaiting_name: Name):
        """Removes awaiting data name from all """
