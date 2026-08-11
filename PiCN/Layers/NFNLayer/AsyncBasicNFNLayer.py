"""Async NFN layer wrapper around NFNLayerCore (ADR-003, ADR-009)."""

import asyncio
from concurrent.futures import Executor
from typing import Dict, Optional

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor
from PiCN.Layers.NFNLayer.NFNLayerCore import NFNCoreResult, NFNLayerCore
from PiCN.Layers.NFNLayer.nfn_executor_io import run_nfn_executor_execute
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.R2C import BaseR2CHandler
from PiCN.Packets import Interest
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncBasicNFNLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`NFNLayerCore`.

    CPU-bound ``BaseNFNExecutor.execute`` runs on an injected stack executor
  via ``run_in_executor`` with a pure helper (ADR-009). ``executor=None`` means
    run execute on the event loop (tests/small workloads).
    """

    def __init__(
        self,
        cs: BaseContentStore,
        fib: BaseForwardingInformationBase,
        pit: BasePendingInterestTable,
        faceidtable: BaseFaceIDTable,
        comp_table: BaseNFNComputationTable,
        executors: Dict[str, BaseNFNExecutor],
        parser: DefaultNFNParser,
        r2c_client: BaseR2CHandler,
        log_level: int = 255,
        executor: Optional[Executor] = None,
    ):
        super().__init__(logger_name="NFN-Layer", log_level=log_level)
        self._core = NFNLayerCore(
            cs=cs,
            fib=fib,
            pit=pit,
            faceidtable=faceidtable,
            comp_table=comp_table,
            executors=executors,
            parser=parser,
            r2c_client=r2c_client,
            logger=self.logger,
        )
        self._executor: Optional[Executor] = executor

    @property
    def executor(self) -> Optional[Executor]:
        return self._executor

    @executor.setter
    def executor(self, value: Optional[Executor]) -> None:
        self._executor = value

    def set_executor(self, executor: Executor) -> None:
        """Injected by AsyncLayerStack.start_all() (ADR-009)."""
        self._executor = executor

    @property
    def cs(self):
        return self._core.cs

    @property
    def fib(self):
        return self._core.fib

    @property
    def pit(self):
        return self._core.pit

    @property
    def faceidtable(self):
        return self._core.faceidtable

    @property
    def computation_table(self):
        return self._core.computation_table

    @property
    def executors(self):
        return self._core.executors

    @property
    def r2cclient(self):
        return self._core.r2cclient

    @property
    def parser(self):
        return self._core.parser

    @property
    def optimizer(self):
        return self._core.optimizer

    @optimizer.setter
    def optimizer(self, value):
        self._core.optimizer = value

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

    async def _run_nfn_execute(self, req) -> Optional[str]:
        if self._executor is not None:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self._executor,
                run_nfn_executor_execute,
                req.nfn_executor,
                req.function_code,
                req.params,
                req.packetid,
                req.comp_name,
            )
        return run_nfn_executor_execute(
            req.nfn_executor,
            req.function_code,
            req.params,
            req.packetid,
            req.comp_name,
        )

    async def _resolve_result_async(
        self, result: NFNCoreResult, to_lower, to_higher
    ) -> None:
        for req in result.pending_executions:
            res = await self._run_nfn_execute(req)
            follow = self._core.compute_with_result(req, res)
            await self._resolve_result_async(follow, to_lower, to_higher)
        for out in result.outbounds:
            await self._apply_outbound(out, to_lower, to_higher)

    async def data_from_higher(
        self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data
    ) -> None:
        result = self._core.handle_from_higher(data)
        await self._resolve_result_async(result, to_lower, to_higher)

    async def data_from_lower(
        self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data
    ) -> None:
        result = self._core.handle_from_lower(data)
        await self._resolve_result_async(result, to_lower, to_higher)

    async def compute(self, interest: Interest) -> None:
        """Run a computation (mirrors sync :meth:`BasicNFNLayer.compute`)."""
        result = self._core.compute(interest)
        await self._resolve_result_async(
            result, self.queue_to_lower, self.queue_to_higher
        )
