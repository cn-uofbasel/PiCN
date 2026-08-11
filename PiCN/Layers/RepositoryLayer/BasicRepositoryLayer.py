"""Basic implementation of the repository layer"""

import multiprocessing

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Layers.RepositoryLayer.RepositoryLayerCore import RepositoryLayerCore
from PiCN.Packets import Packet
from PiCN.Processes import LayerProcess
from PiCN.Processes.Outbound import Outbound


class BasicRepositoryLayer(LayerProcess):
    """Basic implementation of the repository layer

    Thin sync wrapper around :class:`RepositoryLayerCore` (ADR-003 extract-core).
    """

    def __init__(
        self,
        repository: BaseRepository,
        propagate_interest: bool = False,
        logger_name="RepoLayer",
        log_level=255,
    ):
        super().__init__(logger_name, log_level)
        self._core = RepositoryLayerCore(
            repository=repository,
            propagate_interest=propagate_interest,
            logger=self.logger,
        )

    @property
    def repository(self) -> BaseRepository:
        return self._core.repository

    def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            to_lower.put(out.item)
        elif out.direction == "higher":
            to_higher.put(out.item)
        elif out.direction == "queue_lower":
            if self.queue_to_lower is not None:
                self.queue_to_lower.put(out.item)
        elif out.direction == "queue_higher":
            if self.queue_to_higher is not None:
                self.queue_to_higher.put(out.item)

    def data_from_higher(
        self,
        to_lower: multiprocessing.Queue,
        to_higher: multiprocessing.Queue,
        data: Packet,
    ):
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_lower(
        self,
        to_lower: multiprocessing.Queue,
        to_higher: multiprocessing.Queue,
        data: Packet,
    ):
        for out in self._core.handle_from_lower(data):
            self._apply_outbound(out, to_lower, to_higher)
