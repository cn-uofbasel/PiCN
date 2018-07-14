""" An in-memory content store with prefix matching"""

import time

from PiCN.Packets import Content, Name
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry
from PiCN.Layers.ICNLayer.ContentStore.NamedObjectTree import NamedObjectTree


class ContentStoreMemoryPrefix(BaseContentStore):
    """ An in-memory content store with prefix matching"""

    def __init__(self):
        self._container: NamedObjectTree = NamedObjectTree()

    def find_content_object(self, name: Name) -> ContentStoreEntry:
        """
        Lookup a content object (prefix match)
        :param name:  Name
        :return:      Matching Content Object or None
        """
        return self._container.prefix_lookup(name)

    def add_content_object(self, content: Content, static: bool = False):
        """
        Insert content object
        :param content: content object to insert
        :param static: <todo>
        :return: None
        """
        entry = ContentStoreEntry(content, static=static)
        entry.timestamp = time.time()
        self._container.insert(entry)

    def remove_content_object(self, name: Name):
        """
        Remove content object
        :param name: Name (exact)
        :return: None
        """
        self._container.remove(name)

    def update_timestamp(self, cs_entry: ContentStoreEntry):
        """
        Update timestamp
        :param cs_entry: content store entry
        :return: None
        """
        self._container.remove(cs_entry.name)
        cs_entry.timestamp = time.time()
        self._container.insert(cs_entry)

    def ageing(self):
        """
        Update the entries periodically
        :return: None
        """
        raise NotImplemented()
