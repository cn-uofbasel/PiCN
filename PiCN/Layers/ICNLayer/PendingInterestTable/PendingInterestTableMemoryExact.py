"""in-memory Pending Interest Table using exact prefix matching"""

import time

from typing import List
from PiCN.Layers.ICNLayer.PendingInterestTable.BasePendingInterestTable import BasePendingInterestTable, \
    PendingInterestTableEntry
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseEntry
from PiCN.Packets import Interest, Name

class PendingInterstTableMemoryExact(BasePendingInterestTable):
    """in-memory Pending Interest Table using exact prefix matching"""

    def __init__(self, pit_timeout: int=4, pit_retransmits:int=3) -> None:
        super().__init__(pit_timeout=pit_timeout, pit_retransmits=pit_retransmits)

    def add_pit_entry(self, name, faceid: int, interest: Interest = None, local_app = False):
        for pit_entry in self._container:
            if pit_entry.name == name:
                if faceid in pit_entry.face_id and local_app in pit_entry.local_app:
                    return
                self._container.remove(pit_entry)
                pit_entry._faceids.append(faceid)
                pit_entry._local_app.append(local_app)
                self._container.append(pit_entry)
                return
        self._container.append(PendingInterestTableEntry(name, faceid, interest, local_app))

    def remove_pit_entry(self, name: Name):
        to_remove =[]
        for pit_entry in self._container:
            if(pit_entry.name == name):
                to_remove.append(pit_entry)
        for r in to_remove:
            self._container.remove(r)

    def find_pit_entry(self, name: Name) -> PendingInterestTableEntry:
        for pit_entry in self._container:
            if (pit_entry.name == name):
                return pit_entry
        return None

    def update_timestamp(self, pit_entry: PendingInterestTableEntry):
        self._container.remove(pit_entry)
        new_entry = PendingInterestTableEntry(pit_entry.name, pit_entry.faceids, interest=pit_entry.interest, local_app=pit_entry.local_app)
        self._container.append(new_entry)

    def add_used_fib_entry(self, name: Name, used_fib_entry: ForwardingInformationBaseEntry):
        pit_entry = self.find_pit_entry(name)
        self._container.remove(pit_entry)
        pit_entry.fib_entries_already_used.append(used_fib_entry)
        self._container.append(pit_entry)

    def get_already_used_pit_entries(self, name: Name):
        pit_entry = self.find_pit_entry(name)
        return pit_entry.fib_entries_already_used

    def append(self, entry):
        self._container.append(entry)

    def ageing(self) -> List[PendingInterestTableEntry]:
        cur_time = time.time()
        remove = []
        updated = []
        for pit_entry in self._container:
            if pit_entry.timestamp + self._pit_timeout < cur_time and pit_entry.retransmits > self._pit_retransmits:
                remove.append(pit_entry)
            else:
                pit_entry.retransmits = pit_entry.retransmits + 1
                updated.append(pit_entry)
        for pit_entry in remove:
            self.remove_pit_entry(pit_entry.name)
        for pit_entry in updated:
            self.remove_pit_entry(pit_entry.name)
            self._container.append(pit_entry)
        return updated
