"""Index schema parsing, representation and querying"""

import re
from itertools import groupby

from PiCN.Packets.Name import Name


class Rule():
    """ Representation of a rule within an index schema"""

    def __init__(self, pattern, type, wrappers):
        """
        Create new rule object
        :param pattern: Regex
        :param type: Mime type of wrapped high-level object
        :param wrappers: Wrappers applied to content which is published under matching names
        """
        self.pattern = re.compile(pattern)
        self.type = type
        self.wrapper = wrappers

    def check_match(self, name: Name) -> bool:
        """
        Check if a given name matches this rule
        :param name: Name
        :return: True if match, False otherwise
        """
        if isinstance(name, Name): name = name.to_string()
        return True if self.pattern.match(name) is not None else False


class IndexSchema(object):
    """ Representation of an index schema"""

    """
    # Example for an index schema as published as data packet.
    # published as index:/alice/index.schema
    doc:/alice/movies/[^/]+$
        -> wrapper:/irtf/icnrg/flic
        -> wrapper:/alice/homebrewed/ac
             mode="CBC"
             padding="PKCS5"
        => type:/mime/video/webm

    doc:/alice/public/docs/.*[.]pdf$
        -> wrapper:/simple/chunking
        => type:/mime/application/pdf

    doc:/alice/public/img/basel.jpg$
        -> wrapper:/simple/chunking
        => type:/mime/image/jpeg

    """

    def __init__(self, wire_schema: bytearray):
        """
        Create Index schema object from network representation
        :param wire_schema: Index schema as retrieved from network
        """
        lines = wire_schema.split('\n')
        as_list = [list(group) for k, group in groupby(lines, lambda x: x == "") if not k]

        def wrapper_mapper(wrappers):
            wrapper_list = []
            for e in wrappers:
                if e[0:5] == '   ->':
                    wrapper_list.append((e[14:], dict()))
                else:
                    key = e.split('=')[0][7:]
                    value = e.split('=')[1][1:-1]
                    wrapper_list[-1][1][key] = value
            return wrapper_list

        rule_mapper = lambda r: Rule(r[0][4:], r[-1][12:], wrapper_mapper(r[1:-1]))
        self.rules = list(map(rule_mapper, as_list))  # list of Rule objects

    def find_matching_rule(self, name: Name) -> Rule:
        """
        Match a name against this index schema
        :param name: Name to match
        :return: Matching Rule or None
        """
        for r in self.rules:
            if r.check_match(name):
                return r
        return None
