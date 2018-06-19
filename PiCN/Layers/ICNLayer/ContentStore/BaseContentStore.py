"""Abstract BaseContentStore for usage in BasicICNLayer"""

import abc
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
    """Abstract BaseContentStore for usage in BasicICNLayer
    :param cs_timeout: Time interval in which a CS entry will be cached
    """

    def __init__(self, cs_timeout: int=10):
        self._container: List[ContentStoreEntry] = []
        self._cs_timeout = cs_timeout

    @abc.abstractmethod
    def add_content_object(self, content: Content, static: bool=False):
        """
        Insert content object
        :param content: content object to insert
        :param static: if true the conent object will not be considered by ageing
        :return: None
        """

    @abc.abstractmethod
    def find_content_object(self, name: Name) -> ContentStoreEntry:
        """
        Lookup a content object
        :param name:  Name
        :return:      Matching Content Object or None
        """

    @abc.abstractmethod
    def remove_content_object(self, name: Name):
        """
        Remove content object
        :param name: Name (exact)
        :return: None
        """

    @abc.abstractmethod
    def update_timestamp(self, cs_entry: ContentStoreEntry):
        """
        Update timestamp
        :param cs_entry: content store entry
        :return: None
        """
        """Update Timestamp of a ContentStoreEntry"""

    @abc.abstractmethod
    def ageing(self):
        """
        Update the entries periodically
        :return: None
        """

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container
