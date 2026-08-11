"""Async Chunking Layer wrapper around ChunkLayerCore (ADR-003)."""

import asyncio
from typing import Optional

from PiCN.Layers.ChunkLayer.Chunkifyer import BaseChunkifyer
from PiCN.Layers.ChunkLayer.ChunkLayerCore import ChunkLayerCore, RequestTableEntry
from PiCN.Packets import Content
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncBasicChunkLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`ChunkLayerCore`."""

    def __init__(self, chunkifyer: BaseChunkifyer = None, chunk_size: int = 4096, log_level: int = 255):
        super().__init__(logger_name="ChunkLayer", log_level=log_level)
        self._core = ChunkLayerCore(
            chunkifyer=chunkifyer, chunk_size=chunk_size, logger=self.logger)

    @property
    def chunk_size(self):
        return self._core.chunk_size

    @property
    def chunkifyer(self):
        return self._core.chunkifyer

    async def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            await to_lower.put(out.item)
        elif out.direction == "higher":
            await to_higher.put(out.item)

    async def data_from_higher(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        for out in self._core.handle_from_higher(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def data_from_lower(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        for out in self._core.handle_from_lower(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def handle_received_meta_data(self, faceid: int, packet: Content,
                                        request_table_entry: RequestTableEntry,
                                        to_lower: asyncio.Queue) -> RequestTableEntry:
        request_table_entry, outs = self._core.handle_received_meta_data(
            faceid, packet, request_table_entry)
        for out in outs:
            await to_lower.put(out.item)
        return request_table_entry

    async def handle_received_chunk_data(self, faceid: int, packet: Content,
                                         request_table_entry: RequestTableEntry,
                                         to_higher: asyncio.Queue) -> Optional[RequestTableEntry]:
        request_table_entry, outs = self._core.handle_received_chunk_data(
            faceid, packet, request_table_entry)
        for out in outs:
            await to_higher.put(out.item)
        return request_table_entry
