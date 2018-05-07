""" A in memory Forwarding Information Base using longest matching"""

import multiprocessing
from typing import List

from PiCN.Layers.ICNLayer.ForwardingInformationBase.BaseForwardingInformationBase import BaseForwardingInformationBase, \
    ForwardingInformationBaseEntry
from PiCN.Packets import Name, Interest


class ForwardingInformationBaseMemoryPrefix(BaseForwardingInformationBase):

    def __init__(self):
        super().__init__()

    def find_fib_entry(self, name: Name, already_used: List[ForwardingInformationBaseEntry] = None) -> ForwardingInformationBaseEntry:
        components = name.components[:]
        for i in range(0, len(name.components)):
            complen = len(components)
            for fib_entry in self._container:
                if already_used and fib_entry in already_used:
                    continue
                if fib_entry.name.components == components:
                    return fib_entry
            components = components[:complen - 1]
        return None

    def add_fib_entry(self, name: Name, faceid: int, static: bool=False):
        fib_entry = ForwardingInformationBaseEntry(name, faceid, static)
        if fib_entry not in self._container:
            self._container.insert(0, fib_entry)


    def remove_fib_entry(self, name: Name):
        for fib_entry in self._container:
            if fib_entry.name == name:
                self._container.remove(fib_entry)

