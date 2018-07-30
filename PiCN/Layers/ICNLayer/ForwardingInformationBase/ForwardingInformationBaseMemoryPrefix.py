""" A in memory Forwarding Information Base using longest matching"""

from typing import List

from PiCN.Layers.ICNLayer.ForwardingInformationBase.BaseForwardingInformationBase import BaseForwardingInformationBase, \
    ForwardingInformationBaseEntry
from PiCN.Packets import Name


class ForwardingInformationBaseMemoryPrefix(BaseForwardingInformationBase):

    def __init__(self):
        super().__init__()

    def find_fib_entry(self, name: Name, already_used: List[ForwardingInformationBaseEntry] = None,
                       incoming_faceids: List[int]=None) -> ForwardingInformationBaseEntry:
        components = name.components[:]
        for i in range(0, len(name.components)):
            complen = len(components)
            for fib_entry in self._container:
                if already_used and fib_entry in already_used:
                    continue
                forward_faceids = []
                if fib_entry.name.components != components:
                    continue
                for faceid in fib_entry.faceid:
                    if not incoming_faceids or faceid not in incoming_faceids:
                        forward_faceids.append(faceid)
                if len(forward_faceids) == 0:
                    continue
                return ForwardingInformationBaseEntry(fib_entry.name, forward_faceids)
            components = components[:complen - 1]
        return None

    def add_fib_entry(self, name: Name, faceid: List[int], static: bool=False):
        assert (isinstance(faceid, List))
        fib_entry = ForwardingInformationBaseEntry(name, faceid, static)
        if fib_entry not in self._container:
            self._container.insert(0, fib_entry)

    def remove_fib_entry(self, name: Name):
        for fib_entry in self._container:
            if fib_entry.name == name:
                self._container.remove(fib_entry)

    def add_faceid_to_entry(self, name, fid):
        entry = self.find_fib_entry(name)
        self.remove_fib_entry(name)
        if entry is None:
            return
        if fid not in entry.faceid:
            entry.faceid.append(fid)
        self._container.insert(0, entry)

    def clear(self):
        for fib_entry in self._container:
            if not fib_entry.static:
                self._container.remove(fib_entry)
