"""Async autoconfig client layer wrapper (ADR-003)."""

import asyncio
from typing import Optional

from PiCN.Layers.AutoconfigLayer.AutoconfigLayerCore import AutoconfigClientCore
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Packets import Packet
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncAutoconfigClientLayer(AsyncLayerProcess):

    def __init__(
        self,
        linklayer: BasicLinkLayer = None,
        bcport: int = 9000,
        solicitation_timeout: float = None,
        solicitation_max_retry: int = 3,
        log_level: int = 255,
    ):
        super().__init__(logger_name="AutoconfigClientLayer", log_level=log_level)
        self._core = AutoconfigClientCore(
            linklayer=linklayer,
            bcport=bcport,
            solicitation_timeout=solicitation_timeout,
            solicitation_max_retry=solicitation_max_retry,
            logger=self.logger,
        )
        self._solicitation_max_retry = solicitation_max_retry
        self._solicitation_task: Optional[asyncio.Task] = None

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

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            return
        if not isinstance(data[0], int) and data[0] is not None or not isinstance(data[1], Packet):
            return
        fid = data[0]
        packet: Packet = data[1]
        outbounds, solicitation_started = self._core.handle_from_higher(fid, packet)
        for out in outbounds:
            await self._apply_outbound(out, to_lower, to_higher)
        if solicitation_started and self._core.should_schedule_solicitation_retry(self._solicitation_max_retry):
            self._solicitation_task = asyncio.create_task(
                self._solicitation_retry(self._solicitation_max_retry - 1),
                name="AutoconfigClient-solicitation",
            )

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            return
        fid, packet = data
        addr_info = self._core._linklayer.faceidtable.get_address_info(fid)
        for out in self._core.handle_from_lower(fid, packet, addr_info):
            await self._apply_outbound(out, to_lower, to_higher)
        if self._core.should_cancel_solicitation_timer():
            if self._solicitation_task is not None:
                self._solicitation_task.cancel()
                try:
                    await self._solicitation_task
                except asyncio.CancelledError:
                    pass
                self._solicitation_task = None

    async def _solicitation_retry(self, retry: int) -> None:
        await asyncio.sleep(self._core._solicitation_timeout)
        for out in self._core.send_forwarder_solicitation(retry):
            await self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)
        if self._core.should_schedule_solicitation_retry(retry):
            await self._solicitation_retry(retry - 1)

    async def stop(self, timeout: float = None) -> None:
        if self._solicitation_task is not None:
            self._solicitation_task.cancel()
            try:
                await self._solicitation_task
            except asyncio.CancelledError:
                pass
            self._solicitation_task = None
        if timeout is None:
            from PiCN.Processes.AsyncLayerProcess import SHUTDOWN_TIMEOUT
            timeout = SHUTDOWN_TIMEOUT
        await super().stop(timeout=timeout)
