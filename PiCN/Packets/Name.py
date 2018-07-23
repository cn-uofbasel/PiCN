"""Internal representation of network name"""

from typing import List, Union

import binascii
import json
import os
from typing import List, Union

class Name(object):
    """
    Internal representation of network name
    """

    def __init__(self, name: Union[str, List[bytes]] = None, suite='ndn2013'):
        self.suite = suite
        self.digest = None
        if name:
            if isinstance(name, str):
                self.from_string(name)
            else:
                self._components = name
        else:
            self._components = []

    def from_string(self, name: str):
        """Set the name from a string, components separated by /"""
        # FIXME: handle '/' as part of a component, UTF etc
        comps = name.split("/")[1:]
        self._components = [c.encode('ascii') for c in comps]

    def components_to_string(self) -> str:
        # FIXME: handle '/' as part of a component, and binary components
        if len(self._components) == 0:
            return '/'
        if type(self._components[0]) is str:
            s =  '/' + '/'.join([c for c in self._components])
            return s
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

    def __repr__(self) -> str:
        return f'<PiCN.Packets.Name.Name {str(self)} at {hex(id(self))}>'

    def __eq__(self, other) -> bool:
        if type(other) is not Name:
            return False
        if self.suite != other.suite:
            return False
        return self.to_string() == other.to_string()

    def __add__(self, other) -> 'Name':
        components: List[bytes] = []
        for c in self._components:
            components.append(c)
        if type(other) is list:
            for comp in other:
                if type(comp) is str:
                    components.append(comp.encode('ascii'))
                elif type(comp) is bytes:
                    components.append(comp)
                else:
                    raise TypeError('Not a Name, str, List[str] or List[bytes]')
        elif type(other) is str:
                components.append(other.encode('ascii'))
        elif isinstance(other, Name):
            for comp in other._components:
                components.append(comp)
        else:
            raise TypeError('Not a Name, str, List[str] or List[bytes]')
        return Name(components)

    def __hash__(self) -> int:
        return self._components.__str__().__hash__()

    def __len__(self):
        return len(self._components)

    def is_prefix_of(self, name):
        """
        Checks if self is prefix of a given name
        :param name: name
        :return: true if self is prefix of given name, false otherwise
        """
        pfx = os.path.commonprefix([self._components, name._components])
        return len(pfx) == len(self._components)

    def has_prefix(self, name):
        """
        Checks if self has a certain prefix
        :param name: prefix
        :return: true if self has given prefix, false otherwise
        """
        return name.is_prefix_of(self)

    @property
    def components(self):
        """Name components"""
        return self._components

    @components.setter
    def components(self, components):
        self._components = components

    @property
    def string_components(self):
        """Name components"""
        return [c.decode('ascii') for c in self._components]

    @string_components.setter
    def string_components(self, string_components):
        self._components = [c.encode('ascii') for c in string_components]