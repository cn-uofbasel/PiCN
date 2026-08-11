"""This is the BasicThunk layer used to check if it is possible to compute a result, and determine the
cost of computing the result"""

import multiprocessing

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.ThunkLayer.ThunkTable import BaseThunkTable
from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Layers.ThunkLayer.ThunkLayerCore import ThunkLayerCore
from PiCN.Processes import LayerProcess
from PiCN.Processes.Outbound import Outbound


class BasicThunkLayer(LayerProcess):
    """Thunk planning layer.

    Thin sync wrapper around :class:`ThunkLayerCore` (ADR-003 extract-core).
    """

    def __init__(
        self,
        cs: BaseContentStore,
        fib: BaseForwardingInformationBase,
        pit: BasePendingInterestTable,
        faceidtable: BaseFaceIDTable,
        thunkTable: BaseThunkTable,
        planTable: PlanTable,
        parser: DefaultNFNParser,
        repo: BaseRepository = None,
        log_level=255,
    ):
        super().__init__("ThunkLayer", log_level)
        self._core = ThunkLayerCore(
            cs=cs,
            fib=fib,
            pit=pit,
            faceidtable=faceidtable,
            thunk_table=thunkTable,
            plan_table=planTable,
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

    def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            to_lower.put(out.item)
        elif out.direction == "higher":
            to_higher.put(out.item)
        elif out.direction == "queue_lower":
            if self.queue_to_lower is not None:
                self.queue_to_lower.put(out.item)
        elif out.direction == "queue_higher":
            if self.queue_to_higher is not None:
                self.queue_to_higher.put(out.item)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_lower(data):
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

    def removeThunkMarker(self, name):
        return self._core.removeThunkMarker(name)

    def addThunkMarker(self, name):
        return self._core.addThunkMarker(name)

    def generatePossibleThunkNames(self, ast, res=None):
        return self._core.generatePossibleThunkNames(ast, res)

    def all_data_available(self, name):
        return self._core.all_data_available(name)

    def compute_cost_and_requests(self, ast, dataset):
        return self._core.compute_cost_and_requests(ast, dataset)

    def get_data_size(self, name):
        return self._core.get_data_size(name)

    def isthunk(self, name):
        return self._core.isthunk(name)
