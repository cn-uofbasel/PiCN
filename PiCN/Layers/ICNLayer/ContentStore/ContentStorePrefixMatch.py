""" An in-memory content store with prefix matching"""

import multiprocessing, time, sys

from PiCN.Packets import Content, Name
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry
from PiCN.Layers.ICNLayer.ContentStore import ContentTree

class ContentStorePrefixMatch(BaseContentStore):
    """ An in-memory content store with prefix matching"""

    def __init__(self, manager: multiprocessing.Manager = None):
        self._container = ContentTree()

    def find_content_object(self, name: Name) -> ContentStoreEntry:
        return None
        return
        # for c in self._container:
        #     if c.content.name == name: #and c.content.name_payload == name_payload:
        #         return c
        # return None

    def add_content_object(self, content: Content, static: bool=False):
        return None
        # for c in self._container:
        #     if content == c.content:
        #         return
        # self._container.append(ContentStoreEntry(content, static=static))

    def remove_content_object(self, name: Name):
        return None
        # rem = self.find_content_object(name)
        # if rem is not None:
        #     self._container.remove(rem)

    def update_timestamp(self, cs_entry: ContentStoreEntry):
        return None
        # self._container.remove(cs_entry)
        # cs_entry.timestamp = time.time()
        # self._container.append(cs_entry)
