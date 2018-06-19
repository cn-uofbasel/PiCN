""" Data structure to organize named objects in a tree reflecting their namespace hierarchy """

from PiCN.Packets import Name

from functools import reduce
from collections import defaultdict
import operator
import json
from typing import List


def Tree(named_object=None):
    return {"subtree": defaultdict(Tree), "leaf": named_object}

class NamedObjectTree():
    """
    Data structure to organize objects with property 'name' (of type PiCN.Packets.Name) in a tree reflecting their
    namespace hierarchy (e.g. Content, ContentStoreEntry). Exact and prefix lookup is possible.
    """

    def __init__(self):
        """
       Create empty tree
        """
        self.__tree = Tree()

    def __get_subtree(self, path: List[str]):
        """
        Get subtree of a certain path
        :param path: path of subtree to return
        :return: subtree of given path
        """
        if len(path) == 0:
            return self.__tree["subtree"]
        return reduce(lambda subtree, key: operator.getitem(subtree["subtree"], key), path, self.__tree)["subtree"]

    def as_json(self) -> str:
        """
        tree as JSON
        :return: tree as json
        """
        return json.dumps(self.__tree)

    def insert(self, named_object) -> None:
        """
        Insert an object
        :param named_object: Object to insert (must have a property 'name' of type PiCN.Packets.Name)
        :return: None
        """
        path = named_object.name.components
        (self.__get_subtree(path[:-1])[path[-1]])["leaf"] = named_object

    def remove(self, name: Name) -> None:
        """
        Remove an object
        :param name: Name of object to remove
        :return: None
        """
        # TODO: this only removes the leaf (=value) but not nodes (=nested dicts) which are no longer used (if any).
        path = name.components
        del ((self.__get_subtree(path[:-1]))[path[-1]])["leaf"]

    def exact_lookup(self, name: Name):
        """
        Lookup (only exact matches are returned)
        :param name: Name to lookup
        :return: Named object or None
        """
        path = name.components
        try:
            return ((self.__get_subtree(path[:-1]))[path[-1]])["leaf"]
        except KeyError:
            return None

    def prefix_lookup(self, name: Name):
        """
        Find any object which has a given prefix (or exact match)
        :param name: name/prefix
        :return: Named object or None
        """
        def traverse(tree):
            if tree["leaf"] is not None:
                return tree["leaf"]
            else:
                for key in tree["subtree"]:
                    return traverse(tree["subtree"][key])
            return None

        path = name.components
        start = (self.__get_subtree(path[:-1]))[path[-1]]
        return traverse(start)
