"""Basic Routing System, dispatching Interest Content and Routing Packets.
Tickers sending packets to the neigbours."""

from typing import List

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Logger import Logger
from PiCN.Processes import PiCNProcess


class BasicRouting(PiCNProcess):
    """Basic Routing System, dispatching Interest Content and Routing Packets.
    Tickers sending packets to the neigbours."""


    def __init__(self, pit: BasePendingInterestTable, faces: List[str], log_level: int=255):
        self._logger = Logger("Routing", log_level)
        self.pit = pit
        self.faces = faces


    def start_process(self):
        #TODO
        pass

    def stop_process(self):
        # TODO
        pass

