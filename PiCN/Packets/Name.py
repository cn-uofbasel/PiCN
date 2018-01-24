"""Name data structure for PiCN"""

import binascii
import json
import os


class Name(object):
    """Name data structure for PiCN"""

    def __init__(self, name: str = None, suite='ndn2013'):
        self.suite = suite
        self.digest = None
        if name:
            self.from_string(name)
        else:
            self._components = []

    def from_string(self, name: str):
        """Set the name from a string, components separated by /"""
        # FIXME: handle '/' as part of a component, UTF etc
        comps = name.split("/")[1:]
        self._components = [c.encode('ascii') for c in comps]

    def components_to_string(self) -> str:
        # FIXME: handle '/' as part of a component, and binary components
        s = '/' + '/'.join([c.decode('ascii') for c in self._components])
        return s

    def to_string(self) -> str:
        """Transform name to string, components separated by /"""
        s = self.components_to_string()
        if self.digest:
            s += "[hashId=%s]" % binascii.hexlify(self.digest).decode('ascii')
        return s

    def to_json(self) -> str:
        """encoded name as JSON"""
        n = {}
        n['suite'] = self.suite
        n['comps'] = [ binascii.hexlify(c).decode('ascii') for c in self._components ]
        if self.digest:
            n['dgest'] = binascii.hexlify(self.digest).decode('ascii')
        return json.dumps(n)

    def from_json(self, s: str) -> str:
        n = json.loads(s)
        self.suite = n['suite']
        self._components = [ binascii.dehexlify(c) for c in n['comps'] ]
        self.digest = binascii.dehexlify(n['dgest']) if 'dgest' in n else None
        return self

    def setDigest(self, digest : str = None):
        self.digest = digest
        return self
        
    def __str__(self) -> str:
        return self.to_string()

    def __add__(self, other):
        for o in other:
            self._components.append(o)

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
