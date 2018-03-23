""" Data structure to organize content objects in a tree reflecting their namespace hierarchy """

from PiCN.Packets import Content, Name

from functools import reduce
from collections import defaultdict
import operator
import json
from typing import List

class ContentTree():
    """
    Data structure to organize content objects in a tree reflecting their namespace hierarchy.
    """

    def __init__(self):
        """
       Create empty tree
        """
        def Tree(content_object=None):
            return {"subtree": defaultdict(Tree), "leaf": content_object}
        self.__tree = Tree()

    def as_json(self) -> str:
        """
        tree as JSON
        :return: tree as json
        """
        return json.dumps(self.__tree)

    def __get_subtree(self, path: List[str]):
        """
        Get subtree of a certain path
        :param path: path of subtree to return
        :return: subtree of given path
        """
        assert(len(path)>0)
        return reduce(lambda subtree, key: operator.getitem(subtree["subtree"], key), path, self.__tree)["subtree"]

    def insert(self, content: Content) -> None:
        """
        Insert a content object
        :param content: Content object to insert
        :return: None
        """
        path = content.name.components
        (self.__get_subtree(path[:-1])[path[-1]])["leaf"] = content

    def remove(self, name: Name) -> None:
        """
        Remove a content object
        :param name: Name of content object to remove
        :return: None
        """
        # TODO: this only removes the leaf (=value) but not nodes (=nested dicts) which are no longer used (if any).
        path = name.components
        del ((self.__get_subtree(path[:-1]))[path[-1]])["leaf"]

    def exact_lookup(self, name: Name):
        """
        Lookup (only exact matches are returned)
        :param name: Name to lookup
        :return: Content Object or None
        """
        path = name.components
        try:
            return ((self.__get_subtree(path[:-1]))[path[-1]])["leaf"]
        except KeyError:
            return None
