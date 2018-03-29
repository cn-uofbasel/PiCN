""" An in-memory content store with prefix matching"""

import multiprocessing, time, sys

from PiCN.Packets import Content, Name
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry
from PiCN.Layers.ICNLayer.ContentStore import ContentTree

class ContentStorePrefixMatch(BaseContentStore):
    """ An in-memory content store with prefix matching"""

    def __init__(self, manager: multiprocessing.Manager = None):
        self._container:ContentTree = ContentTree() # TODO - this is not yet multiprocessing capable!

    def find_content_object(self, name: Name) -> ContentStoreEntry:
        # todo
        return None

    def add_content_object(self, content: Content, static: bool=False):
        self._container.insert(content)

    def remove_content_object(self, name: Name):
        self._container.remove(name)

    def update_timestamp(self, cs_entry: ContentStoreEntry):
        # TODO
        return None
