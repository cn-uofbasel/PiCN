"""Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

import abc
import multiprocessing
from typing import List

from PiCN.Packets import Name
from PiCN.Layers.ICNLayer import BaseICNDataStruct


class ForwardingInformationBaseEntry(object):
    """An entry in the Forwarding Information Base"""

    def __init__(self, name: Name, faceid: int, static: bool = False):
        self._name: Name = name
        self._faceid: int = faceid
        self._static: bool = static

    def __eq__(self, other):
        return self._name == other._name and self._faceid == other._faceid

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def faceid(self):
        return self._faceid

    @faceid.setter
    def faceid(self, faceid):
        self._faceid = faceid

    @property
    def static(self):
        return self._static

    @static.setter
    def static(self, static):
        self._static = static


class BaseForwardingInformationBase(BaseICNDataStruct):
    """Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

    def __init__(self):
        super().__init__()
        self._container: List[ForwardingInformationBaseEntry] = []

    @abc.abstractmethod
    def add_fib_entry(self, name: Name, fid: int, static: bool):
        """Add an Interest to the PIT"""

    @abc.abstractmethod
    def remove_fib_entry(self, name: Name):
        """Remove an entry from the PIT"""

    @abc.abstractmethod
    def find_fib_entry(self, name: Name, already_used: List[ForwardingInformationBaseEntry]) \
            -> ForwardingInformationBaseEntry:
        """Find an entry in the PIT"""
