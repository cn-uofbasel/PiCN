"""Async timeout-prevention layer wrapper around TimeoutPreventionCore (ADR-003)."""

import asyncio
from typing import Optional

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.TimeoutPreventionLayer.TimeoutPreventionCore import (
    TimeoutPreventionCore,
    TimeoutPreventionMessageDict,
)
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncBasicTimeoutPreventionLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`TimeoutPreventionCore`.

    Ageing uses an asyncio task instead of ``threading.Timer``.
    """

    def __init__(
        self,
        message_dict: TimeoutPreventionMessageDict,
        nfn_comp_table: BaseNFNComputationTable,
        pit: BasePendingInterestTable = None,
        log_level: int = 255,
    ):
        super().__init__(logger_name="TimeoutPrev", log_level=log_level)
        self._core = TimeoutPreventionCore(
            message_dict=message_dict,
            nfn_comp_table=nfn_comp_table,
            pit=pit,
            logger=self.logger,
        )
        self._ageing_task: Optional[asyncio.Task] = None

    @property
    def timeout_interval(self):
        return self._core.timeout_interval

    @timeout_interval.setter
    def timeout_interval(self, value):
        self._core.timeout_interval = value

    @property
    def ageing_interval(self):
        return self._core.ageing_interval

    @ageing_interval.setter
    def ageing_interval(self, value):
        self._core.ageing_interval = value

    @property
    def message_dict(self):
        return self._core.message_dict

    @property
    def computation_table(self):
        return self._core.computation_table

    @computation_table.setter
    def computation_table(self, value):
        self._core.computation_table = value

    @property
    def running_computations(self):
        return self._core.running_computations

    @property
    def pit(self):
        return self._core.pit

    @pit.setter
    def pit(self, value):
        self._core.pit = value

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
        for out in self._core.handle_from_lower(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def _ageing_loop(self) -> None:
        while True:
            await asyncio.sleep(self.ageing_interval)
            for out in self._core.ageing():
                await self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)

    def start(self) -> asyncio.Task:
        task = super().start()
        if self._ageing_task is None or self._ageing_task.done():
            self._ageing_task = asyncio.create_task(
                self._ageing_loop(), name="TimeoutPrevention-ageing"
            )
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
