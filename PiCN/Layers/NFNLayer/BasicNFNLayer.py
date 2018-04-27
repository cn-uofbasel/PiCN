"""Basic NFN Layer Implementation"""
import multiprocessing

from typing import Dict, List

from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Processes import LayerProcess
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationTableEntry
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
        self.icn_data_structs['computation_table']: BaseNFNComputationTable = NFNComputationList(self.r2cclient, self.parser) \
            if computationTable == None else computationTable
        self.optimizer: BaseNFNOptimizer = ToDataFirstOptimizer(self.icn_data_structs)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """handle incomming data from the lower layer """
        packet_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.handleInterest(packet_id, packet)
        elif isinstance(packet, Content):
            self.handleContent(packet_id, packet)
        elif isinstance(packet, Nack):
            self.handleNack(packet_id, packet)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """Currently no higher layer than the NFN Layer
        :param packet_id: id of the computation
        :param interest: content that arrived
        """
        pass

    def handleInterest(self, packet_id: int, interest: Interest):
        """start a new computation from an interest or send it down if no NFN tag
        :param packet_id: id of the computation
        :param interest: interest that arrived
        """
        if self.r2cclient.R2C_identify_Name(interest.name):
            c = self.r2cclient.R2C_handle_request(interest.name)
            if c is not None:
                self.queue_to_lower.put([packet_id, c])
            return
        if interest.name.components[-1] != b"NFN": #send non NFN interests back
            self.queue_to_lower.put([packet_id, interest])
            return
        #parse interest and create computation
        nfn_str, prepended_name = self.parser.network_name_to_nfn_str(interest.name)
        ast = self.parser.parse(nfn_str)
        self.add_computation(interest.name, packet_id, interest, ast)

        #request required data
        required_optimizer_data = self.optimizer.required_data(interest.name, ast)

        self.update_status(interest.name, NFNComputationState.FWD)
        if required_optimizer_data != []: # Optimizer requires additional data
            raise NotImplemented("Global Optimizing not implemeted yet")
            #TODO add to await list, send messages to reqeust data
            return

        #if no data are required we can continue directly, otherwise data handler must call that
        self.forwarding_descision(interest)

    def handleContent(self, packet_id: int, content: Content):
        """handle a arriving content object
        :param packet_id: id of the computation
        :param content: content that arrived
        """
        used = self.push_data(content)
        if not used:
            self.queue_to_lower.put([packet_id, content])
            return

        ready_comps = self.get_ready_computations()
        for comp in ready_comps:
            if comp.comp_state == NFNComputationState.FWD:
                self.forwarding_descision(comp.interest)
            if comp.comp_state == NFNComputationState.EXEC or comp.comp_state == NFNComputationState.WRITEBACK:
                self.compute(comp.interest)


    def handleNack(self, packet_id: int, nack: Nack):
        """Handles a Nack
        :param packet_id: id of the computation
        :param nack: nack that arrived
        """
        remove_list = []
        for e in self.computation_table.container:
            self.remove_computation(e.original_name)
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
            self.append_computation(e)
        #remove all computation that are nack-ed and forward nack
        for r in remove_list:
            e = self.computation_table.get_computation(r)
            self.remove_computation(r)
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
            self.remove_computation(interest.name)
            entry.comp_state = NFNComputationState.REWRITE
            entry.rewrite_list = rewritten_names
            request = self.parser.nfn_str_to_network_name(rewritten_names[0])
            self.queue_to_lower.put([entry.id, Interest(request)])
#            self.handleInterest([entry.id, Interest(request)]) #TODO required?
            self.append_computation(entry)

        if self.optimizer.compute_local(prepended_name, entry.ast):
            self.logger.info("Compute Local")
            self.remove_computation(interest.name)
            entry.comp_state = NFNComputationState.EXEC
            if not isinstance(entry.ast, AST_FuncCall):
                return

            func_name = Name(entry.ast._element)
            entry.add_name_to_await_list(func_name)
            self.queue_to_lower.put([entry.id, Interest(func_name)])

            for p in entry.ast.params:
                name = None
                if isinstance(p, AST_Name):
                    name = Name(p._element)
                    self.queue_to_lower.put([entry.id, Interest(name)])
                elif isinstance(p, AST_FuncCall):
                    #p._prepend = True
                    name = self.parser.nfn_str_to_network_name((str(p)))
                    #p._prepend = False
                    self.handleInterest(entry.id, Interest(name))
                else:
                    continue
                entry.add_name_to_await_list(name)

            self.append_computation(entry)
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
        self.remove_computation(interest.name)
        if entry.comp_state == NFNComputationState.WRITEBACK:
            name = self.parser.nfn_str_to_network_name(entry.rewrite_list[0])
            res = entry.available_data[name]
            data = Content(entry.original_name, res)
            #self.queue_to_lower.put([entry.id, data])
            self.handleContent(entry.id, data)
            return
        function_name = Name(entry.ast._element)
        function_code = entry.available_data.get(function_name)
        if function_code is None:
            self.queue_to_lower.put([entry.id, Nack(entry.original_name,
                                                    NackReason.COMP_PARAM_UNAVAILABLE, interest=entry.interest)])
            return
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
        if res is None:
            self.queue_to_lower.put([entry.id, Nack(entry.original_name, NackReason.COMP_EXCEPTION,
                                                    interest=entry.interest)])
        content_res: Content = Content(entry.original_name, str(res))
        self.queue_to_lower.put([entry.id, content_res])


    def ageing(self):
        """Ageging of the computation queue etc"""
        ct = self.computation_table
        requests, removes = ct.ageing()

        for n in requests:
            self.queue_to_lower.put([0, Interest(n)])

        for n in removes:
            self.queue_to_lower.put(0, Nack(n, NackReason.COMP_TERMINATED, Interest(n)))
        self.computation_table = ct

    @property
    def computation_table(self) -> BaseNFNComputationTable:
        return self.icn_data_structs['computation_table']

    @computation_table.setter
    def computation_table(self, ct):
        self.icn_data_structs['computation_table'] = ct

    def add_computation(self, name: Name, id: int, interest: Interest, ast: AST = None):
        """add a computation to the Computation table (i.e. start a new computation)
        :param name: icn-name of the computation
        :param id: ID given from layer communication
        :param interest: the original interest message
        :param AST: abstract syntax tree of the computation
        """
        ct = self.computation_table
        ct.add_computation(name, id, interest, ast)
        self.computation_table = ct

    def update_status(self, name: Name, status: NFNComputationState):
        """Update the status of a computation giving a name
        :param name: Name of the computation entry to be updated
        :param status: The new Status
        """
        ct = self.computation_table
        ct.update_status(name, status)
        self.computation_table = ct

    def push_data(self, content: Content) -> bool:
        """add received data to running computations
        :param content: content to be added
        :return True if the content was required, else False
        """
        ct = self.computation_table
        res = ct.push_data(content)
        self.computation_table = ct
        return res

    def get_ready_computations(self) -> List[NFNComputationTableEntry]:
        """get all computations that are ready to continue
        :return List of all NFNComputationTableEntrys which are ready
        """
        ct = self.computation_table
        res = ct.get_ready_computations()
        self.computation_table = ct
        return res

    def remove_computation(self, name: Name):
        """Removes a NFNComputationEntry from the container
        :param name: Name of the Computation to be removed
        """
        ct = self.computation_table
        ct.remove_computation(name)
        self.computation_table = ct

    def append_computation(self, entry: NFNComputationTableEntry):
        """Appends a NFNComputationTableEntry if it is not already available in the container
        :param entry: the NFNComputationTableEntry to be appended
        """
        ct = self.computation_table
        ct.append_computation(entry)
        self.computation_table = ct

    def add_awaiting_data(self, name: Name, awaiting_name: Name):
        """Add a name to the await list of a existing computation
        :param name: Name of the existing computation
        "param awaiting_name: Name to be added to the await list.
        """
        ct = self.computation_table
        ct.add_awaiting_data(name, awaiting_name)
        self.computation_table = ct
