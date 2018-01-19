"""Name data structure for PiCN"""

import os
# from functools import reduce

class Name(object):
    """Name data structure for PiCN"""

    def __init__(self, name: str = None, suite='ndn2013'):
        self.suite = suite
        if name:
            self.from_string(name)
        else:
            self._components = []

    def from_string(self, name: str):
        """Set the name from a string, components separated by /"""
        # FIXME: handle '/' as part of a component, UTF etc
        comps = name.split("/")[1:]
        self._components = [c.encode('ascii') for c in comps]

    def to_string(self) -> str:
        """Transform name to string, components separated by /"""
        # FIXME: handle '/' as part of a component, and binary components
        s = '/' + '/'.join([c.decode('ascii') for c in self._components])
        return s

    def __str__(self) -> str:
        return self.to_string()

    def __eq__(self, other) -> bool:
        if type(other) is not Name:
            return False
        if self.suite != other.suite:
            return False
        return self.to_string() == other.to_string()

    def __add__(self, compList):
        for c in compList:
            self._components.append(c)
        return self

    def __hash__(self) -> int:
        return self._components.__str__().__hash__()

    def is_prefix_of(self, name):
        # if type(name) is not Name:
        #    raise XXX
        if  self.suite != name.suite:
            return False
        pfx = os.path.commonprefix([self._components, name._components])
        return len(pfx) == len(self._components)

    @property
    def components(self):
        """Name components"""
        return self._components

    @components.setter
    def components(self, components):
        self._components = components
