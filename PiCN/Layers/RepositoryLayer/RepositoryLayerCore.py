"""Shared repository layer logic (ADR-003 extract-core).

Returns ``List[Outbound]``; does not touch queue objects.
"""

from typing import List, Optional

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Logger import Logger
from PiCN.Packets import Content, Interest, Nack, NackReason
from PiCN.Processes.Outbound import Outbound


class RepositoryLayerCore:
    """Interest-to-content lookup shared by sync and async wrappers."""

    def __init__(
        self,
        repository: Optional[BaseRepository] = None,
        propagate_interest: bool = False,
        logger: Optional[Logger] = None,
    ):
        self._repository: Optional[BaseRepository] = repository
        self._proagate_interest: bool = propagate_interest
        self.logger = logger if logger is not None else Logger("RepoCore", 255)

    @property
    def repository(self) -> Optional[BaseRepository]:
        return self._repository

    @repository.setter
    def repository(self, repository: BaseRepository) -> None:
        self._repository = repository

    @property
    def propagate_interest(self) -> bool:
        return self._proagate_interest

    @propagate_interest.setter
    def propagate_interest(self, value: bool) -> None:
        self._proagate_interest = value

    def handle_from_higher(self, data) -> List[Outbound]:
        return []

    def handle_from_lower(
        self, data, prefetched_content: Optional[Content] = None,
    ) -> List[Outbound]:
        self.logger.info("Got Data from lower")
        if self._repository is None:
            return []
        faceid = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            return self._handle_interest(faceid, packet, prefetched_content)
        if isinstance(packet, Content):
            return []
        return []

    def _handle_interest(
        self,
        faceid: int,
        packet: Interest,
        prefetched_content: Optional[Content],
    ) -> List[Outbound]:
        if self._repository.is_content_available(packet.name):
            if prefetched_content is not None:
                content = prefetched_content
            else:
                content = self._repository.get_content(packet.name)
            self.logger.info("Found content object, sending down")
            return [Outbound("queue_lower", [faceid, content])]
        if self._proagate_interest is True:
            return [Outbound("queue_lower", [faceid, packet])]
        self.logger.info("No matching data, dropping interest, sending nack")
        nack = Nack(packet.name, NackReason.NO_CONTENT, interest=packet)
        return [Outbound("lower", [faceid, nack])]
