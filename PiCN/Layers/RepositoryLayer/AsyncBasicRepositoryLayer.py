"""Async RepositoryLayer wrapper around RepositoryLayerCore (ADR-003)."""

import asyncio
from concurrent.futures import Executor
from typing import Optional

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Layers.RepositoryLayer.Repository.SimpleFileSystemRepository import SimpleFileSystemRepository
from PiCN.Layers.RepositoryLayer.RepositoryLayerCore import RepositoryLayerCore
from PiCN.Layers.RepositoryLayer.repository_file_io import read_file_system_repository_content
from PiCN.Packets import Content, Interest, Name
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncBasicRepositoryLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`RepositoryLayerCore`."""

    def __init__(
        self,
        repository: BaseRepository,
        propagate_interest: bool = False,
        log_level: int = 255,
        executor: Optional[Executor] = None,
    ):
        super().__init__(logger_name="RepoLayer", log_level=log_level)
        self._core = RepositoryLayerCore(
            repository=repository,
            propagate_interest=propagate_interest,
            logger=self.logger,
        )
        self._executor: Optional[Executor] = executor

    @property
    def repository(self) -> BaseRepository:
        return self._core.repository

    @property
    def executor(self) -> Optional[Executor]:
        return self._executor

    @executor.setter
    def executor(self, value: Optional[Executor]) -> None:
        self._executor = value

    def set_executor(self, executor: Executor) -> None:
        """Injected by AsyncLayerStack.start_all() (ADR-009)."""
        self._executor = executor

    async def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            await to_lower.put(out.item)
        elif out.direction == "higher":
            await to_higher.put(out.item)
        elif out.direction == "queue_lower":
            if self.queue_to_lower is not None:
                await self.queue_to_lower.put(out.item)
        elif out.direction == "queue_higher":
            if self.queue_to_higher is not None:
                await self.queue_to_higher.put(out.item)

    async def _get_content_async(self, icnname: Name) -> Optional[Content]:
        repo = self._core.repository
        if repo is None:
            return None
        if self._executor is not None and isinstance(repo, SimpleFileSystemRepository):
            prefix_string = repo._prefix.value.components_to_string()
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self._executor,
                read_file_system_repository_content,
                repo._foldername,
                repo._safepath,
                prefix_string,
                icnname,
            )
        # Default path runs get_content on the event loop. RepositoryLayer tests
        # and typical repo payloads are small (few KB); local reads stay well
        # under ADR-009's ~10 ms blocking threshold, so no executor is required.
        return repo.get_content(icnname)

    async def data_from_higher(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        for out in self._core.handle_from_higher(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def data_from_lower(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        prefetched_content: Optional[Content] = None
        if len(data) >= 2 and self._core.repository is not None:
            packet = data[1]
            if isinstance(packet, Interest) and self._core.repository.is_content_available(packet.name):
                prefetched_content = await self._get_content_async(packet.name)
        for out in self._core.handle_from_lower(data, prefetched_content=prefetched_content):
            await self._apply_outbound(out, to_lower, to_higher)
