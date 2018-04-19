"""Abstract BaseContentStore for usage in BasicICNLayer"""

import abc
import multiprocessing
import time
from typing import List

from PiCN.Packets import Content, Name


class ContentStoreEntry(object):
    """Entry of the content store"""
    def __init__(self, content: Content, static: bool=False):
        self._content: Content = content
        self._static: bool = static #if true: do not remove this content object from CS by ageing
        self._timestamp = time.time()

    @property
    def content(self):
        return self._content

    @property
    def name(self):
        return self._content.name

    @content.setter
    def content(self, content):
        self._content = content

    @property
    def static(self):
        return self._static

    @static.setter
    def static(self, static):
        self._static = static

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = timestamp

    def __eq__(self, other):
        return self._content == other._content

class BaseContentStore(object):
    """Abstract BaseContentStore for usage in BasicICNLayer"""

    def __init__(self):
        self._container: List[ContentStoreEntry] = []

    @abc.abstractmethod
    def add_content_object(self, content: Content, static: bool=False):
        """check if there is already a content object stored, otherwise store it in the container"""

    @abc.abstractmethod
    def find_content_object(self, name: Name) -> ContentStoreEntry:
        """check if there is a matching content object"""

    @abc.abstractmethod
    def remove_content_object(self, name: Name):
        """Remove a content object from CS"""

    @abc.abstractmethod
    def update_timestamp(self, cs_entry: ContentStoreEntry):
        """Update Timestamp of a ContentStoreEntry"""

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container
