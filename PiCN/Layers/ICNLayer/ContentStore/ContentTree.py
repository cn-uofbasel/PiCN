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

    def insert(self, path: List[str], value) -> None:
        """
        Insert a leaf at a given position
        :param path: position where to insert value
        :param value: value to insert in specified leaf
        :return: None
        """
        assert(len(path)>0)
        (self.__get_subtree(path[:-1])[path[-1]])["leaf"] = value

    def remove(self, path: List[str]) -> None:
        """
        Remove a leaf from the tree
        :param path: path of value to remove
        :return: None
        """
        assert(len(path)>0)
        # TODO: this only removes the leaf (=value) but not nodes (=nested dicts) which are no longer used (if any).
        del ((self.__get_subtree(path[:-1]))[path[-1]])["leaf"]

    def exact_lookup(self, path: List[str]):
        """
        Return leaf
        :param path:
        :return:
        """
        assert(len(path)>0)
        return ((self.__get_subtree(path[:-1]))[path[-1]])["leaf"]
