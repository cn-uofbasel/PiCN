"""FLIC Chunkifyer"""

from typing import List

from PiCN.Packets import Packet, Name, Content


class BaseChunkifyer(object):
    """FLIC Chunkifyer"""

    def __init__(self, chunksize=4096):
        self._chunksize = chunksize
        pass

    def chunk_data(self, packet: Packet) -> List[Packet]:
        """Split packet into chunk"""

    def reassamble_data(self, name: Name, chunks: List[Content]) -> Packet:
        """Reassamble chunks"""
