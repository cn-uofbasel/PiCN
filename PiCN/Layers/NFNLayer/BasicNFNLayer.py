"""Basic NFN Layer Implementation"""
import multiprocessing

from typing import Dict

from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Processes import LayerProcess
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationState
from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.NFNLayer.NFNOptimizer import ToDataFirstOptimizer
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler

class BasicNFNLayer(LayerProcess):
    """Basic NFN Layer Implementation"""

    def __init__(self, icn_data_structs: Dict, executors: Dict[str, type(BaseNFNExecutor)],
                 computationTable: BaseNFNComputationTable=None, log_level: int=255):
        super().__init__("NFN-Layer", log_level=log_level)
        self.icn_data_structs = icn_data_structs
        self.executors = executors
        self.r2cclient = TimeoutR2CHandler()
        self.parser: DefaultNFNParser = DefaultNFNParser()
        self.computation_table: BaseNFNComputationTable = NFNComputationList(self.r2cclient, self.parser) \
            if computationTable == None else computationTable
        self.optimizer: BaseNFNOptimizer = ToDataFirstOptimizer(self.icn_data_structs)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """handle incomming data from the lower layer """
        id = data[0]
        packet = data[1]
        if isinstance(data, Interest):
            self.handleInterest(id, data)
        elif isinstance(data, Content):
            self.handleContent(id, data)
        elif isinstance(data, Nack):
            self.handleNack(id, data)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """Currently no higher layer than the NFN Layer"""
        pass

    def handleInterest(self, id: int, interest: Interest):
        """start a new computation from an interest or send it down if no NFN tag"""
        if self.r2cclient.R2C_identify_Name(interest.name):
            c = self.r2cclient.R2C_handle_request(interest.name)
            if c is not None:
                self.queue_to_lower.put([id, c])
            return
        if interest.name.components[-1] != b"NFN": #send non NFN interests back
            self.queue_to_lower.put([id, interest])
            return
        #parse interest and create computation
        nfn_str, prepended_name = self.parser.network_name_to_nfn_str(interest.name)
        ast = self.parser.parse(nfn_str)
        self.computation_table.add_computation(interest.name, id, interest, ast)

        #request required data
        required_optimizer_data = self.optimizer.required_data(interest.name, ast)

        self.computation_table.update_status(interest.name, NFNComputationState.FWD)
        if required_optimizer_data != []: # Optimizer requires additional data
            raise NotImplemented("Global Optimizing not implemeted yet")
            #TODO add to await list, send messages to reqeust data
            return

        #if no data are required we can continue directly, otherwise data handler must call that
        self.forwarding_descision(interest)

    def handleContent(self, id: int, content: Content):
        """handle a arriving content object
        :param id: id of the computation
        :param content: content that arrived
        """
        used = self.computation_table.push_data(content)
        if not used:
            self.queue_to_lower.put([id, content])
            return

        ready_comps = self.computation_table.get_ready_computations()
        for comp in ready_comps:
            if comp.comp_state == NFNComputationState.FWD:
                self.forwarding_descision(comp.interest)
            if comp.comp_state == NFNComputationState.EXEC or comp.comp_state == NFNComputationState.WRITEBACK:
                self.compute(comp.interest)


    def handleNack(self, id: int, nack: Nack):
        """Handles a Nack
        :param id: id of the computation
        :param nack: nack that arrived
        """
        remove_list = []
        for e in self.computation_table.container:
            self.computation_table.remove_computation(e.original_name)
            #check next rewrite if current is nack-ed TODO this is a code duplication with ageing in ComputationTableEntry
            if e.comp_state == NFNComputationState.REWRITE and\
                    e.rewrite_list != [] and\
                    nack.name == self.parser.nfn_str_to_network_name(e.rewrite_list[0]):
                e.rewrite_list.pop(0)
                if e.rewrite_list == []:
                    remove_list.append(e.original_name)
                else:
                    request = Interest(self.parser.nfn_str_to_network_name(e.rewrite_list[0]))
                    self.queue_to_lower.put([e.id, request])
            #check if nack-ed data were required.
            elif nack.name == e.original_name:
                remove_list.append(e.original_name)
            else:
                for a in e.awaiting_data:
                    if nack.name == a.name:
                        remove_list.append(e.original_name)
            self.computation_table.append_computation(e)
        #remove all computation that are nack-ed and forward nack
        for r in remove_list:
            e = self.computation_table.get_computation(r)
            self.computation_table.remove_computation(r)
            new_nack = Nack(e.original_name, nack.reason, interest=e.interest)
            self.queue_to_lower.put([e.id, new_nack])
            self.handleNack(e.id, new_nack)

    def forwarding_descision(self, interest: Interest):
        """Decide weather a computation should be executed locally or be forwarded
        :param interest: The original interest message to be handled (can be taken from computation table)
        """
        nfn_str, prepended_name = self.parser.network_name_to_nfn_str(interest.name)
        entry = self.computation_table.get_computation(interest.name)

        if self.optimizer.compute_fwd(prepended_name, entry.ast):
            self.logger.info("FWD")
            rewritten_names = self.optimizer.rewrite(interest.name, entry.ast)
            self.computation_table.update_status(interest.name, NFNComputationState.REWRITE)
            self.computation_table.remove_computation(interest.name)
            entry.rewrite_list = rewritten_names
            request = self.parser.nfn_str_to_network_name(rewritten_names[0])
            self.queue_to_lower.put([entry.id, Interest(request)])
#            self.handleInterest([entry.id, Interest(request)]) #TODO required?
            self.computation_table.append_computation(entry)

        if self.optimizer.compute_local(prepended_name, entry.ast):
            self.logger.info("Compute Local")
            self.computation_table.update_status(interest.name, NFNComputationState.EXEC)
            self.computation_table.remove_computation(interest.name)
            if not isinstance(entry.ast, AST_FuncCall):
                return

            func_name = Name(entry.ast._element)
            entry.add_name_to_await_list(func_name)
            self.queue_to_lower.put([entry.id, Interest(func_name)])

            for p in entry.ast.params:
                name = None
                if isinstance(p, AST_Name):
                    name = Name(p._element)
                    self.queue_to_lower.put([id, Interest(name)])
                elif isinstance(p, AST_FuncCall):
                    #p._prepend = True
                    name = self.parser.nfn_str_to_network_name((str(p)))
                    #p._prepend = False
                    self.handleInterest(id, Interest(name))
                else:
                    continue
                entry.add_name_to_await_list(name)

            self.computation_table.append_computation(entry)
            if(entry.awaiting_data == []):
                self.compute(interest)

    def get_nf_code_language(self, function: str):
        """extract the programming language of a function
        :param function: function data
        """
        language = function.split("\n")[0]
        return language

    def compute(self, interest: Interest):
        """Compute a result, when all data are available
        :param interest: The original interest message to be handled (can be taken from computation table)
        """
        params = []
        entry = self.computation_table.get_computation(interest.name)
        self.computation_table.remove_computation(interest.name)
        if entry.comp_state == NFNComputationState.WRITEBACK:
            name = self.parser.nfn_str_to_network_name(entry.rewrite_list[0])
            res = entry.available_data[name]
            data = Content(entry.original_name, res)
            self.queue_to_lower.put([entry.id, data])
            self.handleContent(entry.id, data)
            return
        function_name = Name(entry.ast._element)
        function_code = entry.available_data.get(function_name)
        if function_code is None:
            self.queue_to_lower.put([entry.id, Nack(entry.original_name,
                                                    NackReason.COMP_PARAM_UNAVAILABLE, interest=entry.interest)])
            return #TODO NACK
        executor: BaseNFNExecutor = self.executors.get(self.get_nf_code_language(function_code))
        if executor is None:
            self.queue_to_lower.put([entry.id, Nack(entry.original_name, NackReason.COMP_EXCEPTION, interest=entry.interest)])
        for e in entry.ast.params:
            if isinstance(e, AST_Name):
                param = entry.available_data.get(Name(e._element))
                if param is None:
                    self.queue_to_lower.put([entry.id, Nack(entry.original_name, NackReason.COMP_PARAM_UNAVAILABLE,
                                                            interest=entry.interest)])
                    return
                params.append(param)
            elif isinstance(e, AST_FuncCall):
                search_name = Name()
                search_name += str(e)
                search_name += "NFN"
                params.append(entry.available_data[search_name])
            elif not isinstance(e.type, AST):
                params.append(e.type(e._element))

        res = executor.execute(function_code, params)
        content_res: Content = Content(entry.original_name, str(res))
        self.queue_to_lower.put([entry.id, content_res])

