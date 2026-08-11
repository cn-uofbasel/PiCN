"""Shared NFN layer logic (ADR-003 extract-core).

Returns :class:`NFNCoreResult` (outbounds plus optional deferred executor work);
does not touch queue objects.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.NFNLayer.NFNComputationTable import (
    BaseNFNComputationTable,
    NFNComputationState,
    NFNComputationTableEntry,
)
from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.NFNLayer.NFNOptimizer import ToDataFirstOptimizer
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.NFNLayer.R2C import BaseR2CHandler
from PiCN.Logger import Logger
from PiCN.Packets import Content, Interest, Nack, NackReason, Name
from PiCN.Processes.Outbound import Outbound


@dataclass
class NFNExecutionRequest:
    """Deferred NFN function execution (resolved by sync/async wrappers)."""

    nfn_executor: BaseNFNExecutor
    function_code: str
    params: List
    packetid: int
    comp_name: Name
    original_name: Name
    entry_interest: Interest


@dataclass
class NFNCoreResult:
    """Outbounds and optional CPU-bound work for wrappers to run."""

    outbounds: List[Outbound] = field(default_factory=list)
    pending_executions: List[NFNExecutionRequest] = field(default_factory=list)

    def extend(self, other: "NFNCoreResult") -> None:
        self.outbounds.extend(other.outbounds)
        self.pending_executions.extend(other.pending_executions)


class NFNLayerCore:
    """NFN computation logic shared by sync and async wrappers."""

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
        logger: Optional[Logger] = None,
    ):
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self.faceidtable = faceidtable
        self.computation_table = comp_table
        self.executors = executors
        self.r2cclient = r2c_client
        self.parser: DefaultNFNParser = parser
        self.optimizer: BaseNFNOptimizer = ToDataFirstOptimizer(
            self.cs, self.fib, self.pit, self.faceidtable
        )
        self.logger = logger if logger is not None else Logger("NFNCore", 255)

    def handle_from_higher(self, data) -> NFNCoreResult:
        return NFNCoreResult()

    def handle_from_lower(self, data) -> NFNCoreResult:
        if isinstance(data, list):
            packet_id = data[0]
            packet = data[1]
        else:
            packet_id = 1
            packet = data
        if isinstance(packet, Interest):
            self.logger.info(
                "Got Interest from lower: " + str(packet.name) + "; Face ID: " + str(packet_id)
            )
            return self.handle_interest(packet_id, packet)
        if isinstance(packet, Content):
            self.logger.info("Got Content from lower: " + str(packet.name))
            return self.handle_content(packet_id, packet)
        if isinstance(packet, Nack):
            self.logger.info("Got Nack from lower: " + str(packet.name))
            return self.handle_nack(packet_id, packet)
        return NFNCoreResult()

    def handle_interest(self, packet_id: int, interest: Interest) -> NFNCoreResult:
        result = NFNCoreResult()
        if self.r2cclient.R2C_identify_Name(interest.name):
            c = self.r2cclient.R2C_handle_request(interest.name, self.computation_table)
            if c is not None:
                if packet_id < 0:
                    self.computation_table.push_data(c)
                else:
                    result.outbounds.append(Outbound("queue_lower", [packet_id, c]))
            return result
        if interest.name.components[-1] != b"NFN":
            result.outbounds.append(Outbound("queue_lower", [packet_id, interest]))
            return result
        nfn_str, prepended_name = self.parser.network_name_to_nfn_str(interest.name)
        ast = self.parser.parse(nfn_str)

        if self.computation_table.add_computation(interest.name, packet_id, interest, ast) is False:
            self.logger.info("Computation already running")
            return result
        self.logger.info(
            "#Running Computations: " + str(self.computation_table.get_container_size())
        )
        required_optimizer_data = self.optimizer.required_data(interest.name, ast)

        self.computation_table.update_status(interest.name, NFNComputationState.FWD)
        if required_optimizer_data != []:
            raise NotImplemented("Global Optimizing not implemeted yet")

        result.extend(self.forwarding_descision(interest))
        return result

    def handle_content(self, packet_id: int, content: Content) -> NFNCoreResult:
        result = NFNCoreResult()
        self.logger.info("Handeling Content: " + str(content.name))
        used = self.computation_table.push_data(content)
        if not used:
            result.outbounds.append(Outbound("queue_lower", [packet_id, content]))
            return result

        ready_comps = self.computation_table.get_ready_computations()
        for comp in ready_comps:
            if comp.comp_state == NFNComputationState.FWD:
                result.extend(self.forwarding_descision(comp.interest))
            if comp.comp_state == NFNComputationState.EXEC or comp.comp_state == NFNComputationState.WRITEBACK:
                result.extend(self.compute(comp.interest))
        return result

    def handle_nack(self, packet_id: int, nack: Nack) -> NFNCoreResult:
        result = NFNCoreResult()
        remove_list = []
        for e in self.computation_table.get_container():
            self.computation_table.remove_computation(e.original_name)
            if (
                e.comp_state == NFNComputationState.REWRITE
                and e.rewrite_list != []
                and nack.name == self.parser.nfn_str_to_network_name(e.rewrite_list[0])
            ):
                e.rewrite_list.pop(0)
                if e.rewrite_list == []:
                    remove_list.append(e.original_name)
                elif e.rewrite_list[0] == "local":
                    self.logger.info("No rewrite left, compute local")
                    result.extend(self.fetch_parameter_and_compute_local(e.interest, e))
                    return result
                else:
                    request = Interest(self.parser.nfn_str_to_network_name(e.rewrite_list[0]))
                    result.outbounds.append(Outbound("queue_lower", [packet_id, request]))
            elif nack.name == e.original_name:
                remove_list.append(e.original_name)
            else:
                for a in e.awaiting_data:
                    if nack.name == a.name:
                        remove_list.append(e.original_name)
            self.computation_table.append_computation(e)
        for r in remove_list:
            e = self.computation_table.get_computation(r)
            self.computation_table.remove_computation(r)
            new_nack = Nack(e.original_name, nack.reason, interest=e.interest)
            result.outbounds.append(Outbound("queue_lower", [packet_id, new_nack]))
            result.extend(self.handle_nack(e.id, new_nack))
        return result

    def forwarding_descision(self, interest: Interest) -> NFNCoreResult:
        result = NFNCoreResult()
        nfn_str, prepended_name = self.parser.network_name_to_nfn_str(interest.name)
        entry = self.computation_table.get_computation(interest.name)

        if self.optimizer.compute_fwd(prepended_name, entry.ast, interest):
            self.logger.info("Forward Computation: " + str(interest.name))
            rewritten_names = self.optimizer.rewrite(interest.name, entry.ast)
            if rewritten_names and len(rewritten_names) > 0:
                self.computation_table.remove_computation(interest.name)
                entry.comp_state = NFNComputationState.REWRITE
                entry.rewrite_list = rewritten_names
                request = self.parser.nfn_str_to_network_name(rewritten_names[0])
                result.outbounds.append(Outbound("queue_lower", [entry.id, Interest(request)]))
                self.computation_table.append_computation(entry)

        if self.optimizer.compute_local(prepended_name, entry.ast, interest):
            self.computation_table.remove_computation(interest.name)
            result.extend(self.fetch_parameter_and_compute_local(interest, entry))
        return result

    def fetch_parameter_and_compute_local(
        self, interest: Interest, computation_table_entry: NFNComputationTableEntry
    ) -> NFNCoreResult:
        result = NFNCoreResult()
        self.logger.info("Compute Local: " + str(interest.name))
        computation_table_entry.comp_state = NFNComputationState.EXEC
        if not isinstance(computation_table_entry.ast, AST_FuncCall):
            self.logger.error(
                "AST is no function call but: " + str(computation_table_entry.ast)
            )
            nack = Nack(interest.name, reason=NackReason.COMP_NOT_PARSED, interest=interest)
            result.extend(self.handle_nack(computation_table_entry.id, nack))
            result.outbounds.append(Outbound("queue_lower", [computation_table_entry.id, nack]))
            return result

        func_name = Name(computation_table_entry.ast._element)
        computation_table_entry.add_name_to_await_list(func_name)
        result.outbounds.append(
            Outbound("queue_lower", [computation_table_entry.id, Interest(func_name)])
        )

        for p in computation_table_entry.ast.params:
            name = None
            if isinstance(p, AST_Name):
                name = Name(p._element)
                result.outbounds.append(
                    Outbound("queue_lower", [computation_table_entry.id, Interest(name)])
                )
            elif isinstance(p, AST_FuncCall):
                name = self.parser.nfn_str_to_network_name((str(p)))
                self.logger.info("Subcomputation: " + str(name))
                result.extend(
                    self.handle_interest(computation_table_entry.id, Interest(name))
                )
            else:
                continue
            computation_table_entry.add_name_to_await_list(name)

        self.computation_table.append_computation(computation_table_entry)
        if computation_table_entry.awaiting_data == []:
            result.extend(self.compute(interest))
        return result

    def get_nf_code_language(self, function: str) -> str:
        language = function.split("\n")[0]
        return language

    def compute(self, interest: Interest) -> NFNCoreResult:
        """Prepare computation; execution is deferred via :class:`NFNExecutionRequest`."""
        result = NFNCoreResult()
        self.logger.info("Start computation: " + str(interest.name))
        entry = self.computation_table.get_computation(interest.name)
        if entry is None:
            self.logger.info("Cannot compute because no computation table entry")
            return result
        self.computation_table.remove_computation(interest.name)
        if entry.comp_state == NFNComputationState.WRITEBACK:
            self.logger.info("Writeback computation to incoming name")
            name = self.parser.nfn_str_to_network_name(entry.rewrite_list[0])
            res = entry.available_data[name]
            data = Content(entry.original_name, res)
            result.extend(self.handle_content(entry.id, data))
            return result

        prep_result, execution_request = self._prepare_execution(entry, interest)
        result.extend(prep_result)
        if execution_request is not None:
            result.pending_executions.append(execution_request)
        return result

    def compute_with_result(
        self, request: NFNExecutionRequest, res: Optional[str]
    ) -> NFNCoreResult:
        """Finish computation after executor returns."""
        if res is None:
            return NFNCoreResult(
                outbounds=[
                    Outbound(
                        "queue_lower",
                        [
                            request.packetid,
                            Nack(
                                request.original_name,
                                NackReason.COMP_EXCEPTION,
                                interest=request.entry_interest,
                            ),
                        ],
                    )
                ]
            )
        content_res = Content(request.original_name, str(res))
        self.logger.info("Finish Computation: " + str(content_res.name))
        return self.handle_content(request.packetid, content_res)

    def _prepare_execution(
        self, entry: NFNComputationTableEntry, interest: Interest
    ) -> Tuple[NFNCoreResult, Optional[NFNExecutionRequest]]:
        result = NFNCoreResult()
        params: List = []
        function_name = Name(entry.ast._element)
        function_code = entry.available_data.get(function_name)
        if function_code is None:
            self.logger.info("Cannot compute, because function code is not available")
            result.outbounds.append(
                Outbound(
                    "queue_lower",
                    [
                        entry.id,
                        Nack(
                            entry.original_name,
                            NackReason.COMP_PARAM_UNAVAILABLE,
                            interest=entry.interest,
                        ),
                    ],
                )
            )
            return result, None
        nfn_executor = self.executors.get(self.get_nf_code_language(function_code))
        if nfn_executor is None:
            self.logger.info(
                "Cannot compute, because executor is not available for language: "
                + self.get_nf_code_language(function_code)
            )
            result.outbounds.append(
                Outbound(
                    "queue_lower",
                    [
                        entry.id,
                        Nack(
                            entry.original_name,
                            NackReason.COMP_EXCEPTION,
                            interest=entry.interest,
                        ),
                    ],
                )
            )
            return result, None
        for e in entry.ast.params:
            if isinstance(e, AST_Name):
                param = entry.available_data.get(Name(e._element))
                if param is None:
                    self.logger.info("Cannot compute, because parameter is not available")
                    result.outbounds.append(
                        Outbound(
                            "queue_lower",
                            [
                                entry.id,
                                Nack(
                                    entry.original_name,
                                    NackReason.COMP_PARAM_UNAVAILABLE,
                                    interest=entry.interest,
                                ),
                            ],
                        )
                    )
                    return result, None
                params.append(param)
            elif isinstance(e, AST_FuncCall):
                search_name = Name()
                search_name += str(e)
                search_name += "NFN"
                params.append(entry.available_data[search_name])
            elif not isinstance(e.type, AST):
                params.append(e.type(e._element))
        request = NFNExecutionRequest(
            nfn_executor=nfn_executor,
            function_code=function_code,
            params=params,
            packetid=entry.id,
            comp_name=interest.name,
            original_name=entry.original_name,
            entry_interest=entry.interest,
        )
        return result, request

    def ageing(self) -> NFNCoreResult:
        result = NFNCoreResult()
        requests, removes = self.computation_table.ageing()

        for n in requests:
            if type(n) is str:
                continue
            name = n
            if "_" in "".join(name.string_components):
                result.extend(self.handle_interest(0, Interest(name)))
            else:
                result.extend(self.handle_interest(-1, Interest(name)))
        for n in removes:
            if type(n) is str:
                name = self.parser.nfn_str_to_network_name(n)
            else:
                name = n
            nack = Nack(n, NackReason.COMP_TERMINATED, interest=Interest(name))
            result.outbounds.append(Outbound("queue_lower", [n.id, nack]))
        return result
