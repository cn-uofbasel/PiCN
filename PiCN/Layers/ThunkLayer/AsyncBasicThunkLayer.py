"""Async thunk planning layer wrapper around ThunkLayerCore (ADR-003)."""

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Layers.ThunkLayer.ThunkLayerCore import ThunkLayerCore
from PiCN.Layers.ThunkLayer.ThunkTable import BaseThunkTable
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncBasicThunkLayer(AsyncLayerProcess):
    """Async thin wrapper around :class:`ThunkLayerCore`."""

    def __init__(
        self,
        cs: BaseContentStore,
        fib: BaseForwardingInformationBase,
        pit: BasePendingInterestTable,
        faceidtable: BaseFaceIDTable,
        thunk_table: BaseThunkTable,
        plan_table: PlanTable,
        parser: DefaultNFNParser,
        repo: BaseRepository = None,
        log_level: int = 255,
    ):
        super().__init__(logger_name="ThunkLayer", log_level=log_level)
        self._core = ThunkLayerCore(
            cs=cs,
            fib=fib,
            pit=pit,
            faceidtable=faceidtable,
            thunk_table=thunk_table,
            plan_table=plan_table,
            parser=parser,
            repo=repo,
            logger=self.logger,
        )

    @property
    def cs(self):
        return self._core.cs

    @cs.setter
    def cs(self, value):
        self._core.cs = value

    @property
    def fib(self):
        return self._core.fib

    @fib.setter
    def fib(self, value):
        self._core.fib = value

    @property
    def pit(self):
        return self._core.pit

    @pit.setter
    def pit(self, value):
        self._core.pit = value

    @property
    def faceidtable(self):
        return self._core.faceidtable

    @faceidtable.setter
    def faceidtable(self, value):
        self._core.faceidtable = value

    @property
    def parser(self):
        return self._core.parser

    @property
    def optimizer(self):
        return self._core.optimizer

    @property
    def repo(self):
        return self._core.repo

    @repo.setter
    def repo(self, value):
        self._core.repo = value

    @property
    def active_thunk_table(self):
        return self._core.active_thunk_table

    @property
    def planTable(self):
        return self._core.planTable

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
