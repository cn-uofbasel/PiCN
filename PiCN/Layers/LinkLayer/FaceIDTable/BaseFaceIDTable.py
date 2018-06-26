"""Abstract superclass for FaceID Tables"""

import abc

from PiCN.Layers.LinkLayer.Interfaces import AddressInfo

class BaseFaceIDTable(object):
    """Abstract superclass for FaceID Tables"""

    def __init__(self):
        self.current_face_id = 0
        self.max_entries = int(1e4)


    @abc.abstractmethod
    def get_address_info(self, faceid: int) -> AddressInfo:
        """returns the address info given a faceid
        :param faceid: face ID to identify the address info
        :return: The corresponding Address info, or None if no entry found
        """

    @abc.abstractmethod
    def get_face_id(self, address_info: AddressInfo) -> int:
        """returns a face id given an address info
        :param address_info: address_info to identify the faceid
        :return: The corresponding face id, or None if no entry found
        """

    @abc.abstractmethod
    def add(self, faceid: int, address_info: AddressInfo):
        """adds an entry to the FaceIDTable
        :param faceid: faceid of the new entry
        :param address_info: address info of the new entry
        :return: none
        """

    @abc.abstractmethod
    def remove(self, faceid: int):
        """removes an entry from the FaceID Table
        :param faceid: faceid to identify the entry to be removed.
        :return none
        """

    @abc.abstractmethod
    def remove_oldest(self):
        """removes the oldest entry if no space is left in the datastruct"""

    def get_or_create_faceid(self, address_info: AddressInfo) -> int:
        """adds and entry and automatically selects a faceid or if an entry exits select that entry
        :param address_info: address info of the new entry
        :return: faceid that was selected, if an entry already exists, returns the existing faceid
        """
        fid = self.get_face_id(address_info)
        if fid is not None:
            return fid
        self.remove_oldest()
        self.current_face_id += 1
        self.add(self.current_face_id, address_info)
        return  self.current_face_id
