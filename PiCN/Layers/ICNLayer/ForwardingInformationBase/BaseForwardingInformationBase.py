"""Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

import abc
import multiprocessing
from typing import List

from PiCN.Packets import Name


class ForwardingInformationBaseEntry(object):
    """An entry in the Forwarding Information Base"""

    def __init__(self, name: Name, faceid: int, static: bool=False):
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

class BaseForwardingInformationBase(object):
    """Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

    def __init__(self):
        self._container: List[ForwardingInformationBaseEntry] = []

    @abc.abstractmethod
    def add_fib_entry(self, name: Name, fid: int, static: bool):
        """Add an Interest to the FIB"""

    @abc.abstractmethod
    def remove_fib_entry(self, name: Name):
        """Remove an entry from the FIB"""

    @abc.abstractmethod
    def find_fib_entry(self, name: Name, already_used: List[ForwardingInformationBaseEntry]) \
            ->ForwardingInformationBaseEntry:
        """Find an entry in the FIB"""

    @abc.abstractmethod
    def clear(self):
        """Remove all non-static entries from the FIB"""

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def manager(self):
        return self._manager

    @manager.setter
    def manager(self, manager: multiprocessing.Manager):
        self._manager = manager
