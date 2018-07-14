"""Base Class for all ICN Data Structs"""

from typing import List


class BaseICNDataStruct(object):
    def __init__(self):
        self._container = None

    def get_container_size(self) -> int:
        """get the current number of entries
        ":return: number of entries
        """
        return len(self.container)

    def get_container(self) -> List:
        """returns the container storing data in the datastruct
        :return: The container
        """
        return self.container

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container
