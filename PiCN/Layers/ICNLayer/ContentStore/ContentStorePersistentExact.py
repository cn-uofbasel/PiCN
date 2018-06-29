""" An persistent content store with exact matching"""

import time
import shelve
import random
import string

from PiCN.Packets import Content, Name
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry


class ContentStorePersistentExact(BaseContentStore):
    """ A persistent content store with exact matching"""

    def __init__(self, cs_timeout: int = 10, db_path: str = None):
        if db_path is None:
            self.db_path = "/tmp/" + ''.join(random.choice(string.ascii_lowercase) for x in range(9)) + ".db"
        else:
            self.db_path = db_path
        self._container = shelve.open(self.db_path)
        self._cs_timeout = cs_timeout

    def close_cs(self):
        self._container.close()

    def get_db_path(self) -> str:
        return self.db_path

    def find_content_object(self, name: Name) -> ContentStoreEntry:
        if name.to_string() in self._container.keys():
            return self._container[name.to_string()]
        else:
            return None

    def add_content_object(self, content: Content, static: bool = False):
        self._container[content.name.to_string()] = ContentStoreEntry(content, static=static)

    def remove_content_object(self, name: Name):
        if name.to_string() in self._container.keys():
            del self._container[name.to_string()]

    def update_timestamp(self, cs_entry: ContentStoreEntry):
        self.remove_content_object(cs_entry.name)
        cs_entry.timestamp = time.time()
        self._container[cs_entry.name.to_string()] = cs_entry

    def ageing(self):
        keys_to_remove = []
        cur_time = time.time()
        for key in self._container:
            if self._container[key].static is True:
                continue
            if self._container[key].timestamp + self._cs_timeout < cur_time:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self.remove_content_object(self._container[key].name.to_string())
