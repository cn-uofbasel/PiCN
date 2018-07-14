"""Basic implementation of the repository layer"""

import multiprocessing

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Interest, Content, Packet, Nack, NackReason
from PiCN.Processes import LayerProcess


class BasicRepositoryLayer(LayerProcess):
    """Basic implementation of the repository layer"""

    def __init__(self, repository: BaseRepository, propagate_interest: bool = False, logger_name="RepoLayer",
                 log_level=255):
        super().__init__(logger_name, log_level)

        self._repository: BaseRepository = repository
        self._proagate_interest: bool = propagate_interest

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data: Packet):
        pass  # do not expect this to happen, since repository is highest layer

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data: Packet):
        self.logger.info("Got Data from lower")
        if self._repository is None:
            return
        faceid = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            if self._repository.is_content_available(packet.name):
                c = self._repository.get_content(packet.name)
                self.queue_to_lower.put([faceid, c])
                self.logger.info("Found content object, sending down")
                return
            elif self._proagate_interest is True:
                self.queue_to_lower.put([faceid, packet])
                return
            else:
                self.logger.info("No matching data, dropping interest, sending nack")
                nack = Nack(packet.name, NackReason.NO_CONTENT, interest=packet)
                to_lower.put([faceid, nack])
                return
        if isinstance(packet, Content):
            pass
