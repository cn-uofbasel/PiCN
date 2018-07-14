""" An in-memory content store with exact matching"""

import time

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry
from PiCN.Packets import Content, Name


class ContentStoreMemoryExact(BaseContentStore):
    """ A in memory Content Store using exact matching"""

    def __init__(self, cs_timeout: int = 10):
        BaseContentStore.__init__(self, cs_timeout=cs_timeout)

    def find_content_object(self, name: Name) -> ContentStoreEntry:
        for c in self._container:
            if c.content.name == name:  # and c.content.name_payload == name_payload:
                return c
        return None

    def add_content_object(self, content: Content, static: bool = False):
        for c in self._container:
            if content == c.content:
                return
        self._container.append(ContentStoreEntry(content, static=static))

    def remove_content_object(self, name: Name):
        rem = self.find_content_object(name)
        if rem is not None:
            self._container.remove(rem)

    def update_timestamp(self, cs_entry: ContentStoreEntry):
        self._container.remove(cs_entry)
        cs_entry.timestamp = time.time()
        self._container.append(cs_entry)

    def ageing(self):
        cur_time = time.time()
        remove = []
        for cs_entry in self._container:
            if cs_entry.static is True:
                continue
            if cs_entry.timestamp + self._cs_timeout < cur_time:
                remove.append(cs_entry)
        for cs_entry in remove:
            self.remove_content_object(cs_entry.content.name)
