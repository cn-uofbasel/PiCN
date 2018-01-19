"""Name data structure for PiCN"""

import os
# from functools import reduce

class Name(object):
    """Name data structure for PiCN"""

    def __init__(self, name: str = None):
        self._components = []
        if name is not None:
            self.set_name(name)

    def set_name(self, name: str):
        """Set the name from a string, components separated by /"""
        comps = name.split("/")
        self._components = comps[1:]

    def to_string(self) -> str:
        """Transform name to string, components separated by /"""
        # FIXME: handle '/' as part of a component, and binary components
        s = '/' + '/'.join(self._components)
        return s

    def __str__(self) -> str:
        return self.to_string()

    def __eq__(self, other) -> bool:
        if type(other) is not Name:
            return False
        return self.to_string() == other.to_string()

    def __add__(self, compList):
        for c in compList:
            self._components.append(c)

    def __hash__(self) -> int:
        return self._components.__str__().__hash__()

    def is_prefix_of(self, name):
        # if type(name) is not Name:
        #    raise XXX
        pfx = os.path.commonprefix([self._components, name._components])
        return len(pfx) == len(self._components)

    @property
    def components(self):
        """Name components"""
        return self._components

    @components.setter
    def components(self, components):
        self._components = components
