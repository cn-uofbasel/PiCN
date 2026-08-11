"""Async ICN Forwarding Layer wrapper around ICNLayerCore (ADR-003)."""

import asyncio
from typing import Optional

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ICNLayerCore import ICNLayerCore
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncBasicICNLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`ICNLayerCore`.

    Ageing uses an asyncio task instead of ``threading.Timer``.
    """

    def __init__(self, cs: BaseContentStore = None, pit: BasePendingInterestTable = None,
                 fib: BaseForwardingInformationBase = None, rib: BaseRoutingInformationBase = None,
                 log_level: int = 255, ageing_interval: int = 3):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        self._core = ICNLayerCore(cs=cs, pit=pit, fib=fib, rib=rib, logger=self.logger)
        self._ageing_interval = ageing_interval
        self._ageing_task: Optional[asyncio.Task] = None

    @property
    def cs(self):
        return self._core.cs

    @cs.setter
    def cs(self, value):
        self._core.cs = value

    @property
    def pit(self):
        return self._core.pit

    @pit.setter
    def pit(self, value):
        self._core.pit = value

    @property
    def fib(self):
        return self._core.fib

    @fib.setter
    def fib(self, value):
        self._core.fib = value

    @property
    def rib(self):
        return self._core.rib

    @rib.setter
    def rib(self, value):
        self._core.rib = value

    @property
    def _interest_to_app(self) -> bool:
        return self._core._interest_to_app

    @_interest_to_app.setter
    def _interest_to_app(self, value: bool):
        self._core._interest_to_app = value

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

    async def data_from_higher(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        for out in self._core.handle_from_higher(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def data_from_lower(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        for out in self._core.handle_from_lower(data, has_to_higher=to_higher is not None):
            await self._apply_outbound(out, to_lower, to_higher)

    async def _ageing_loop(self) -> None:
        while True:
            await asyncio.sleep(self._ageing_interval)
            for out in self._core.ageing():
                await self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)

    def start(self) -> asyncio.Task:
        task = super().start()
        if self._ageing_task is None or self._ageing_task.done():
            self._ageing_task = asyncio.create_task(self._ageing_loop(), name="ICNLayer-ageing")
        return task

    async def stop(self, timeout: float = None) -> None:
        if self._ageing_task is not None:
            self._ageing_task.cancel()
            try:
                await self._ageing_task
            except asyncio.CancelledError:
                pass
            self._ageing_task = None
        if timeout is None:
            from PiCN.Processes.AsyncLayerProcess import SHUTDOWN_TIMEOUT
            timeout = SHUTDOWN_TIMEOUT
        await super().stop(timeout=timeout)
