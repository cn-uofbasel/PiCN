"""Basic NFN Layer Implementation"""
import multiprocessing
import random

from typing import Dict, List

from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Processes import LayerProcess
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationState
from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.NFNLayer.NFNOptimizer import ToDataFirstOptimizer
from PiCN.Layers.NFNLayer.R2C import BaseR2CHandler
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable

class BasicNFNLayer(LayerProcess):
    """Basic NFN Layer Implementation"""

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable,
                 comp_table: BaseNFNComputationTable, executors: Dict[str, type(BaseNFNExecutor)],
                 parser: DefaultNFNParser, r2c_client: BaseR2CHandler, log_level: int=255):
        super().__init__("NFN-Layer", log_level=log_level)
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self.faceidtable = faceidtable
        self.computation_table = comp_table
        self.executors = executors
        self.r2cclient = r2c_client
        self.parser: DefaultNFNParser = parser
        self.optimizer: BaseNFNOptimizer = ToDataFirstOptimizer(self.cs, self.fib, self.pit, self.faceidtable)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """handle incomming data from the lower layer """
        packet_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.logger.info("Got Interest from lower: " + str(packet.name) + "; Face ID: " + str(packet_id))
            self.handleInterest(packet_id, packet)
        elif isinstance(packet, Content):
            self.logger.info("Got Content from lower: " + str(packet.name))
            self.handleContent(packet_id, packet)
        elif isinstance(packet, Nack):
            self.logger.info("Got Nack from lower: " + str(packet.name))
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
            c = self.r2cclient.R2C_handle_request(interest.name, self.computation_table)
            if c is not None:
                if packet_id < 0:
                    self.computation_table.push_data(c) #local request
                else:
                    self.queue_to_lower.put([packet_id, c])
            return
        if interest.name.components[-1] != b"NFN": #send non NFN interests back
            self.queue_to_lower.put([packet_id, interest])
            return
        #parse interest and create computation
        nfn_str, prepended_name = self.parser.network_name_to_nfn_str(interest.name)
        ast = self.parser.parse(nfn_str)

        if self.computation_table.add_computation(interest.name, packet_id, interest, ast) == False:
            self.logger.info("Computation already running")
            return
        #request required data
        required_optimizer_data = self.optimizer.required_data(interest.name, ast)

        self.computation_table.update_status(interest.name, NFNComputationState.FWD)
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
        self.logger.info("Handeling Content: " + str(content.name))
        used = self.computation_table.push_data(content)
        if not used:
            self.queue_to_lower.put([packet_id, content])
            return

        ready_comps = self.computation_table.get_ready_computations()
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
        for e in self.computation_table.get_container():
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
                    self.queue_to_lower.put([packet_id, request])
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
            self.queue_to_lower.put([packet_id, new_nack])
            self.handleNack(e.id, new_nack)

    def forwarding_descision(self, interest: Interest):
        """Decide weather a computation should be executed locally or be forwarded
        :param interest: The original interest message to be handled (can be taken from computation table)
        """
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
                self.queue_to_lower.put([entry.id, Interest(request)])
#               self.handleInterest([entry.id, Interest(request)]) #TODO required?
                self.computation_table.append_computation(entry)

        if self.optimizer.compute_local(prepended_name, entry.ast, interest):
            self.logger.info("Compute Local: " + str(interest.name))
            self.computation_table.remove_computation(interest.name)
            entry.comp_state = NFNComputationState.EXEC
            if not isinstance(entry.ast, AST_FuncCall):
                self.logger.error("AST is no function call but: " + str(entry.ast))
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
                    self.logger.info("Subcomputation: " + str(name))
                    self.handleInterest(entry.id, Interest(name))
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
        self.logger.info("Start computation: " + str(interest.name))
        params = []
        entry = self.computation_table.get_computation(interest.name)
        if entry is None:
            return
        self.computation_table.remove_computation(interest.name)
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
            self.queue_to_lower.put([entry.id, Nack(entry.original_name, NackReason.COMP_PARAM_UNAVAILABLE,
                                                    interest=entry.interest)])
            return
        executor: BaseNFNExecutor = self.executors.get(self.get_nf_code_language(function_code))
        if executor is None:
            self.queue_to_lower.put([entry.id,
                                     Nack(entry.original_name, NackReason.COMP_EXCEPTION, interest=entry.interest)])
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

        res = executor.execute(function_code=function_code, params=params)
        if res is None:
            self.queue_to_lower.put([entry.id,
                                     Nack(entry.original_name, NackReason.COMP_EXCEPTION, interest=entry.interest)])
        content_res: Content = Content(entry.original_name, str(res)) #TODO typed results
        self.logger.info("Finish Computation: " + str(content_res.name))
        #self.computation_table.push_data(content_res)
        #self.queue_to_lower.put([entry.id, content_res])
        self.handleContent(entry.id, content_res)

    def ageing(self):
        """Ageging of the computation queue etc"""
        requests, removes = self.computation_table.ageing()

        for n in requests:
            if type(n) is str:
                continue
            else:
                name = n
            if '_' in ''.join(name.string_components): #sth is broken here, so this is just a quick fix
                self.handleInterest(0, Interest(name))
            else:
                self.handleInterest(-1, Interest(name))
        for n in removes:
            if type(n) is str:
                name = self.parser.nfn_str_to_network_name(n)
            else:
                name = n
            nack = Nack(n, NackReason.COMP_TERMINATED, interest=Interest(name))
            #self.handleNack(-1, nack)
            self.queue_to_lower.put([n.id, nack])

