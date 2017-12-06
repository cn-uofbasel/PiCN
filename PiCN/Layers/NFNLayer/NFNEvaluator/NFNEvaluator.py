"""NFN Evaluator for PiCN"""

import multiprocessing
import select
import time
from typing import Dict

from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import BaseNFNExecutor
from PiCN.Processes import PiCNProcess
from PiCN.Packets import Content, Interest, Name


class NFNEvaluator(PiCNProcess):
    """NFN Dispatcher for PiCN"""

    def __init__(self, optimizer: BaseNFNOptimizer, interest: Interest):
        self.interest: Interest = interest
        self.computation_in_queue: multiprocessing.Queue = multiprocessing.Queue()  # data to computation
        self.computation_out_queue: multiprocessing.Queue = multiprocessing.Queue()  # data from computation
        self.start_time = time.time()
        self.content_table: Dict[Name, Content] = {}
        self.request_table: List[Name] = []

        self.parser: DefaultNFNParser = DefaultNFNParser()
        self.optimizer: BaseNFNOptimizer = optimizer
        self.executor: Dict[str, type(BaseNFNExecutor)] = {}

    def stop_process(self):
        pass

    def start_process(self):
        self.process = multiprocessing.Process(target=self._run, args=[self.interest.name])


    def _run(self, name: Name): #TODO Must be changed
        res = self.evaluate(name)
        content = Content(name, res)
        self.computation_out_queue.put(content)

    def evaluate(self, name: Name): #TODO Must be changed
        """Run the evaluation process"""
        name_str: str = self.parser.network_name_to_nfn_str(name)
        ast: AST = self.parser.parse(name_str)

        if self.optimizer.compute_local(ast) or isinstance(ast, AST_Name):
            #request child nodes
            if isinstance(ast, AST_FuncCall):
                return
            params = []
            for p in ast.params:
                params.append(self.evaluate(p)) #TODO start a new process for each subcomputation
            functioncode = None #todo fetch code
            executor = self.executor[self.get_nf_code_language(functioncode)]()
            executor.execute(functioncode, params)
            pass
        if self.optimizer.compute_fwd(ast):

            computation_str = self.optimizer.rewrite(ast)
            name = self.parser.nfn_str_to_network_name(computation_str)
            interest = Interest(name)
            content = self.await_data([interest])
            return content[0].content

    def get_nf_code_language(self, function: str):
        """extract the programming language of a function"""
        #TODO return language of the named function
        pass

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
