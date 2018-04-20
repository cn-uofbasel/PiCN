"""in-memory Pending Interest Table using exact prefix matching"""

import time

from PiCN.Layers.ICNLayer.PendingInterestTable.BasePendingInterestTable import BasePendingInterestTable, \
    PendingInterestTableEntry
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseEntry
from PiCN.Packets import Interest, Name

class PendingInterstTableMemoryExact(BasePendingInterestTable):
    """in-memory Pending Interest Table using exact prefix matching"""

    def __init__(self) -> None:
        super().__init__()

    def add_pit_entry(self, name, faceid: int, interest: Interest = None, local_app = False):
        for pit_entry in self._container:
            if pit_entry.name == name:
                if faceid in pit_entry.face_id:
                    return
                self._container.remove(pit_entry)
                pit_entry._faceids.append(faceid)
                pit_entry._local_app.append(local_app)
                self._container.append(pit_entry)
                return
        self._container.append(PendingInterestTableEntry(name, faceid, interest, local_app))

    def remove_pit_entry(self, name: Name):
        for pit_entry in self._container:
            if(pit_entry.name == name):
                self._container.remove(pit_entry)

    def find_pit_entry(self, name: Name) -> PendingInterestTableEntry:
        for pit_entry in self._container:
            if (pit_entry.name == name):
                return pit_entry
        return None

    def update_timestamp(self, pit_entry: PendingInterestTableEntry):
        self._container.remove(pit_entry)
        pit_entry.timestamp = time.time()
        pit_entry.retransmits = 0
        self._container.append(pit_entry)

    def add_used_fib_entry(self, name: Name, used_fib_entry: ForwardingInformationBaseEntry):
        pit_entry = self.find_pit_entry(name)
        self._container.remove(pit_entry)
        pit_entry.fib_entries_already_used.append(used_fib_entry)
        self._container.append(pit_entry)

    def get_already_used_pit_entries(self, name: Name):
        pit_entry = self.find_pit_entry(name)
        return pit_entry.fib_entries_already_used

