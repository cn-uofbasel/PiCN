"""Implementation of a FaceIDTable using a Double Dict"""

import time

from typing import Dict

from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo


class FaceIDDict(BaseFaceIDTable):
    """Implementation of a FaceIDTable using a Double Dict"""

    def __init__(self):
        super().__init__()
        self.faceid_to_addrinfo: Dict[int, AddressInfo] = {}
        self.addrinfo_to_faceid: Dict[AddressInfo, int] = {}
        self.faceids = []

    def get_address_info(self, faceid: int) -> AddressInfo:
        return self.faceid_to_addrinfo.get(faceid)

    def get_face_id(self, address_info: AddressInfo) -> int:
        return self.addrinfo_to_faceid.get(address_info)

    def add(self, faceid: int, address_info: AddressInfo):
        if faceid not in self.faceid_to_addrinfo and address_info not in self.addrinfo_to_faceid:
            self.faceid_to_addrinfo[faceid] = address_info
            self.addrinfo_to_faceid[address_info] = faceid
            self.faceids.append(faceid)

    def remove(self, faceid: int):
        if faceid in self.faceid_to_addrinfo:
            addr_info = self.get_address_info(faceid)
            try:
                addr_info.inferface.close()
            except:
                pass
            del self.faceid_to_addrinfo[faceid]
            del self.addrinfo_to_faceid[addr_info]
            self.faceids.remove(faceid)

    def remove_oldest(self):
        if len(self.faceids) < self.max_entries or len(self.faceids) <= 0:
            return
        self.remove(self.faceids[0])
