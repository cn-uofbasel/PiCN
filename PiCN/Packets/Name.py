"""Name data structure for PiCN"""

from functools import reduce

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
        string =  "/" + reduce((lambda x, y: x + "/" + y), self._components)
        return string

    def __str__(self) -> str:
        return self.to_string()

    def __eq__(self, other) -> bool:
        if type(other) is not Name:
            return False
        return self.to_string() == other.to_string()

    def __hash__(self) -> int:
        return self._components.__str__().__hash__()

    @property
    def components(self):
        """Name components"""
        return self._components

    @components.setter
    def components(self, components):
        self._components = components
