"""NFN Evaluator for PiCN"""

import multiprocessing
import select
import time
from typing import Dict

from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNOptimizer import BaseNFNOptimizer, ToDataFirstOptimizer
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import BaseNFNExecutor
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Processes import PiCNProcess
from PiCN.Packets import Content, Interest, Name


class NFNEvaluator(PiCNProcess):
    """NFN Dispatcher for PiCN"""

    def __init__(self, interest: Interest, cs: BaseContentStore, fib: BaseForwardingInformationBase,
                 pit: BasePendingInterestTable):
        super().__init__("NFNEvaluator", 255)
        self.interest: Interest = interest
        self.computation_in_queue: multiprocessing.Queue = multiprocessing.Queue()  # data to computation
        self.computation_out_queue: multiprocessing.Queue = multiprocessing.Queue()  # data from computation
        self.start_time = time.time()
        self.content_table: Dict[Name, Content] = {}
        self.request_table: List[Name] = []

        self.cs: BaseContentStore = cs
        self.fib: BaseForwardingInformationBase = fib
        self.pit: BasePendingInterestTable = pit

        self.parser: DefaultNFNParser = DefaultNFNParser()
        self.optimizer: BaseNFNOptimizer = None
        self.executor: Dict[str, type(BaseNFNExecutor)] = {}

    def stop_process(self):
        if self.process:
            self.process.terminate()
        pass

    def start_process(self):
        self.process = multiprocessing.Process(target=self._run, args=[self.interest.name])
        self.process.start()

    def _run(self, name: Name): #TODO Must be changed
        res = self.evaluate(name)
        content = Content(name, res)
        self.computation_out_queue.put(content)

    def evaluate(self, name: Name): #TODO Must be changed
        """Run the evaluation process"""
        name_str, prepended = self.parser.network_name_to_nfn_str(name)
        ast: AST = self.parser.parse(name_str)
        self.optimizer = ToDataFirstOptimizer(prepended, self.cs, self.fib, self.pit)

        if self.optimizer.compute_fwd(ast): #TODO use rewrite table, froward and return no result
            computation_str = self.optimizer.rewrite(ast)
            name = self.parser.nfn_str_to_network_name(computation_str)
            interest = Interest(name)
            content = self.await_data([interest])
            return content[0].content

        if self.optimizer.compute_local(ast):
            #request child nodes
            if isinstance(ast, AST_Name):
                return
            params_requests = []
            params = []
            for p in ast.params:
                i = self.request_param(p)
                if i is not None:
                    params_requests.append(i)
            if len(params_requests) > 0:
                params_data = self.await_data(params_requests)
                for p in params_data:
                    params.append(p.content)

            functionname = Name(ast._element)
            functionname_i = Interest(functionname)
            self.request_data(functionname_i)
            functioncode_packet = self.await_data([functionname_i])
            functioncode = functioncode_packet[0].content
            language = self.get_nf_code_language(functioncode)
            executor = self.executor.get(language)
            if executor:
                res = executor.execute(functioncode, params)
                return res
            return None

    def get_nf_code_language(self, function: str):
        """extract the programming language of a function"""
        language = function.split("\n")[0]
        return language

    def request_param(self, ast: AST):
        """Request the result of a subcomputation"""
        if isinstance(ast, AST_Name):
            name = Name(ast._element)
        elif isinstance(ast, AST_FuncCall):
            ast._prepend = True
            name = self.parser.nfn_str_to_network_name(str(ast))
            ast._prepend = False
        else:
            return None
        interest = Interest(name)
        self.request_data(interest)
        return interest


    def request_data(self, interest):
        """Request data from the network"""
        self.computation_out_queue.put(interest)
        self.request_table.append(interest.name)

    def await_data(self, interests: List[Interest]) -> List[Content]:
        """Await all pending data"""
        poller = select.poll()
        READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
        poller.register(self.computation_in_queue._reader, READ_ONLY)
        while not self.data_in_content_table(interests):
            ready_vars = poller.poll()
            for filno, var in ready_vars:
                if filno == self.computation_in_queue._reader.fileno() and not self.computation_in_queue.empty():
                    data = self.computation_in_queue.get()
                    if data.name in self.request_table:
                        self.content_table[data.name] = data
                    else:
                        continue
        res = []
        for i in interests:
            res.append(self.content_table.get(i.name))
        return res

    def data_in_content_table(self, interests: List[Interest]):
        """check if data list is available in the content list"""
        for i in interests:
            if i.name not in self.content_table:
                return False
        return True
