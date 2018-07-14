"""Base Class for PiCN Repositories"""

import abc

from PiCN.Packets import Content, Name

class BaseRepository:
    """Base Class for PiCN Repositories"""
    pass

    def __init__(self):
        pass


    @abc.abstractclassmethod
    def is_content_available(self, icnname: Name) -> bool:
        """check if a content object is available in the repo"""

    @abc.abstractclassmethod
    def get_content(self, icnname: Name) -> Content:
        """Get a content object from the repo"""