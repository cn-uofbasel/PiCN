"""Superclass für the Chunkifyer"""

import abc
from typing import List

from PiCN.Packets import Packet, Name, Content

class BaseChunkifyer(object):
    """Superclass für the Chunkifyer"""

    def __init__(self, chunksize = 4096):
        self._chunksize = chunksize
        pass

    @abc.abstractclassmethod
    def chunk_data(self, packet: Packet) -> List[Packet]:
        """Split packet into chunk"""

    @abc.abstractclassmethod
    def reassamble_data(self, name: Name, chunks: List[Content]) -> Packet:
        """Reassamble chunks"""
