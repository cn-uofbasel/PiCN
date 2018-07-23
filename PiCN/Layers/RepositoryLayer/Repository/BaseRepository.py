"""Base Class for PiCN Repositories"""

import abc

from PiCN.Packets import Content, Name


class BaseRepository:
    """Base Class for PiCN Repositories"""
    pass

    def __init__(self):
        pass

    @abc.abstractmethod
    def is_content_available(self, icnname: Name) -> bool:
        """check if a content object is available in the repo"""

    @abc.abstractmethod
    def get_content(self, icnname: Name) -> Content:
        """Get a content object from the repo"""

    @abc.abstractmethod
    def set_prefix(self, prefix: Name):
        """Set the prefix for the repo"""
