"""Basic NFN Layer Implementation"""

import asyncio
import multiprocessing

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
from PiCN.Processes import LayerProcess
from PiCN.Processes.Outbound import Outbound


class BasicNFNLayer(LayerProcess):
    """Basic NFN Layer Implementation.

    Thin sync wrapper around :class:`NFNLayerCore` (ADR-003 extract-core).
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
    ):
        super().__init__("NFN-Layer", log_level=log_level)
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

    def _resolve_result(
        self, result: NFNCoreResult, to_lower, to_higher
    ) -> None:
        for req in result.pending_executions:
            res = run_nfn_executor_execute(
                req.nfn_executor,
                req.function_code,
                req.params,
                req.packetid,
                req.comp_name,
            )
            follow = self._core.compute_with_result(req, res)
            self._resolve_result(follow, to_lower, to_higher)
        for out in result.outbounds:
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_lower(
        self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data
    ):
        result = self._core.handle_from_lower(data)
        self._resolve_result(result, to_lower, to_higher)

    def data_from_higher(
        self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data
    ):
        result = self._core.handle_from_higher(data)
        self._resolve_result(result, to_lower, to_higher)

    def handleInterest(self, packet_id: int, interest: Interest):
        result = self._core.handle_interest(packet_id, interest)
        self._resolve_result(result, self.queue_to_lower, self.queue_to_higher)

    def handleContent(self, packet_id: int, content):
        result = self._core.handle_content(packet_id, content)
        self._resolve_result(result, self.queue_to_lower, self.queue_to_higher)

    def handleNack(self, packet_id: int, nack):
        result = self._core.handle_nack(packet_id, nack)
        self._resolve_result(result, self.queue_to_lower, self.queue_to_higher)

    def forwarding_descision(self, interest: Interest):
        result = self._core.forwarding_descision(interest)
        self._resolve_result(result, self.queue_to_lower, self.queue_to_higher)

    def fetch_parameter_and_compute_local(self, interest: Interest, computation_table_entry):
        result = self._core.fetch_parameter_and_compute_local(
            interest, computation_table_entry
        )
        self._resolve_result(result, self.queue_to_lower, self.queue_to_higher)

    def get_nf_code_language(self, function: str):
        return self._core.get_nf_code_language(function)

    def compute(self, interest: Interest):
        result = self._core.compute(interest)
        self._resolve_result(result, self.queue_to_lower, self.queue_to_higher)

    def ageing(self):
        result = self._core.ageing()
        self._resolve_result(result, self.queue_to_lower, self.queue_to_higher)
