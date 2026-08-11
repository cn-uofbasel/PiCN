"""Async routing layer wrapper around RoutingLayerCore (ADR-003)."""

import asyncio
from typing import List, Optional, Tuple

from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.RoutingLayer.RoutingLayerCore import RoutingLayerCore
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncBasicRoutingLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`RoutingLayerCore`.

    RIB ageing and routing interests use an asyncio task instead of ``threading.Timer``.
    """

    def __init__(
        self,
        linklayer: BasicLinkLayer,
        peers: List[Tuple[str, int]] = None,
        log_level: int = 255,
        ageing_interval: float = 5.0,
    ):
        super().__init__(logger_name="BasicRoutingLayer", log_level=log_level)
        self._core = RoutingLayerCore(linklayer=linklayer, peers=peers, logger=self.logger)
        self._ageing_interval = ageing_interval
        self._ageing_task: Optional[asyncio.Task] = None

    @property
    def rib(self) -> BaseRoutingInformationBase:
        return self._core.rib

    @rib.setter
    def rib(self, value: BaseRoutingInformationBase):
        self._core.rib = value

    @property
    def fib(self) -> BaseForwardingInformationBase:
        return self._core.fib

    @fib.setter
    def fib(self, value: BaseForwardingInformationBase):
        self._core.fib = value

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
        for out in self._core.handle_from_higher(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        for out in self._core.handle_from_lower(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def _ageing_loop(self) -> None:
        while True:
            for out in self._core.ageing_and_solicit():
                await self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)
            await asyncio.sleep(self._ageing_interval)

    def start(self) -> asyncio.Task:
        task = super().start()
        if self._ageing_task is None or self._ageing_task.done():
            self._ageing_task = asyncio.create_task(self._ageing_loop(), name="RoutingLayer-ageing")
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
