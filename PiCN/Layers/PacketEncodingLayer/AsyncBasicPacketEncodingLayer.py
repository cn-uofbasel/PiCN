"""Async PacketEncodingLayer wrapper around PacketEncodingCore (ADR-003)."""

import asyncio

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Layers.PacketEncodingLayer.PacketEncodingCore import PacketEncodingCore
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess


class AsyncBasicPacketEncodingLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`PacketEncodingCore`."""

    def __init__(self, encoder: BasicEncoder = None, log_level: int = 255):
        super().__init__(logger_name="PktEncLayer", log_level=log_level)
        self._core = PacketEncodingCore(encoder=encoder, logger=self.logger)

    @property
    def encoder(self):
        return self._core.encoder

    @encoder.setter
    def encoder(self, encoder):
        self._core.encoder = encoder

    async def data_from_higher(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        for out in self._core.handle_from_higher(data):
            q = to_lower if out.direction == "lower" else to_higher
            await q.put(out.item)

    async def data_from_lower(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        for out in self._core.handle_from_lower(data):
            q = to_lower if out.direction == "lower" else to_higher
            await q.put(out.item)

    def encode(self, data):
        return self._core.encode(data)

    def decode(self, data):
        return self._core.decode(data)
