"""This is the BasicThunk layer used to check if it is possible to compute a result, and determine the
cost of computing the result"""
import multiprocessing
import sys

from typing import List

from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList, ThunkTableEntry, BaseThunkTable
from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable

class BasicThunkLayer(LayerProcess):

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable, thunkTable: BaseThunkTable, planTable: PlanTable, parser: DefaultNFNParser, repo: BaseRepository=None, log_level=255):
        super().__init__("ThunkLayer", log_level)
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self.faceidtable = faceidtable
        self.parser = parser
        self.optimizer = BaseNFNOptimizer(self.cs, self.fib, self.pit, self.faceidtable)
        self.repo = repo
        self.active_thunk_table = thunkTable
        self.planTable = planTable

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        packet_id = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            self.handleInterest(packet_id, packet, from_higher=False)
        elif isinstance(packet, Content):
            self.handleContent(packet_id, packet, from_higher=False)
        elif isinstance(packet, Nack):
            self.handleNack(packet_id, packet, from_higher=False)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        to_lower.put(data)
        return

    def handleInterest(self, id: int, interest: Interest, from_higher):

        data_size = self.get_data_size(interest.name)
        if data_size is not None:
            content = Content(interest.name, "DataSize:" + str(data_size))
            self.queue_to_lower.put(content)
            return

        if not self.isthunk(interest.name):
            if from_higher:
                self.queue_to_lower.put([id, interest])
                return
            else:
                self.queue_to_higher.put([id, interest])
            return

        name = self.removeThunkMarker(interest.name)
        nfn_name = self.parser.network_name_to_nfn_str(name)
        ast = self.parser.parse(nfn_name)

        thunk_names = list(map(lambda x: self.addThunkMarker(self.parser.nfn_str_to_network_name(x)))
                           ,self.generatePossibleThunkNames(ast))

        self.active_thunk_table.add_entry_to_thunk_table(name, id, thunk_names) #Create new computation
        for tn in thunk_names:
            data_size = self.get_data_size(self.removeThunkMarker(tn))
            if data_size is not None:
                content = Content(interest.name, "DataSize:" + str(data_size))
                self.active_thunk_table.add_estimated_cost_to_awaiting_data(name, data_size) #if data local -> set cost
                continue
            interest = Interest(tn)
            self.queue_to_lower.put([id, interest])
        self.check_and_compute_cost()

    def handleContent(self, id: int, content: Content, from_higher):
        #check if content is required if yes add to list, otherwise directly to upper
        #check if all data are available after adding the content.
        if not self.isthunk(content.name):
            if from_higher:
                self.queue_to_lower.put([id, content])
                return
            else:
                self.queue_to_higher.put([id, content])
            return
        if from_higher: #only expect thunk content from lower
            self.queue_to_lower.put([id, content])
        try:
            cost = int(content.content)
        except:
            cost = sys.maxsize
        self.active_thunk_table.add_estimated_cost_to_awaiting_data(content.name, cost)
        self.check_and_compute_cost()

    def check_and_compute_cost(self):
        """check if all data are available and start computation"""
        removes = []
        for e in self.active_thunk_table.container:
            if self.all_data_available(e.name):
                name = self.removeThunkMarker(e.name)
                nfn_name = self.parser.network_name_to_nfn_str(name)
                ast = self.parser.parse(nfn_name)
                cost, path = self.compute_cost_and_requests(ast)
                self.planTable.add_plan(e.name, path, cost)
                removes.append(e)
                content = Content(e.name, str(cost))
                self.queue_to_lower.put([e.id, content])
        for r in removes:
            self.active_thunk_table.remove_entry_from_thunk_table(r.name)

    def handleNack(self, id: int, nack: Nack, from_higher):
        if not self.isthunk(nack.name):
            if from_higher:
                self.queue_to_lower.put([id, nack])
                return
            else:
                self.queue_to_higher.put([id, nack])
            return
        request_name = self.removeThunkMarker(nack.name)
        self.active_thunk_table.remove_awaiting_data(request_name) #got nack for the entry, remove it
        removes = []
        for e in self.active_thunk_table.container: #remove entrys which cannot be solved anymore
            if len(self.active_thunk_table.get_entry_from_name(e.name).awaiting_data) == 0:
                removes.append(e)
            self.check_and_compute_cost()
        for e in removes:
            self.active_thunk_table.remove_entry_from_thunk_table(e.name)
            nack = Nack(e.name, NackReason.NO_ROUTE, Interest(e.name))
            self.queue_to_lower.put([e.id, nack])


    def get_data_size(self, name: Name) -> int:
        cs_entry = self.cs.find_content_object(name) #if content is available local in CS, use it
        data_size = None
        if cs_entry is not None:
            if cs_entry.content.content.startswith(b"mdo:"):
                entry_splits = cs_entry.content.content.split(b":")
                if len(entry_splits) > 2:
                    data_size = int(entry_splits[1])
            else:
                data_size = len(cs_entry.content.content)
        if self.repo is not None:
            if self.repo.is_content_available(name):
                data_size = self.repo.get_data_size(name)
        return data_size

    def removeThunkMarker(self, name: Name) -> Name:
        """Remove the Thunk Marker from a Name"""
        if len(name.components) < 2 or name.components[-2] != b"THUNK":
            return name
        ret = Name(name.components[:])
        del ret.components[-2]
        return ret

    def addThunkMarker(self, name: Name) -> Name:
        """Add a thunk marker to a Name"""
        if len(name.components) < 2 or name.components[-2] == b"THUNK":
            return name
        ret = Name(name.components[:])
        ret.components.append(ret.components[-1])
        ret.components[-2] = b"THUNK"
        return ret

    def generatePossibleThunkNames(self, ast: AST, res: List = None) -> List:
        """Generate names that can be used for the planning"""
        if res == None:
            res = []
        if isinstance(ast, AST_FuncCall):
            name_list = self.optimizer._get_names_from_ast(ast)
            function_list = self.optimizer._get_functions_from_ast(ast)
            prepend_list = name_list + function_list
            fib_name_list = []
            if self.fib.find_fib_entry(Name(ast._element)):
                res.append(ast._element)
            for n in prepend_list:
                if self.fib.find_fib_entry(Name(n)) is not None:
                   fib_name_list.append(n)
            for name in fib_name_list:
                n = self.optimizer._set_prepended_name(ast, Name(name), ast)
                if n is not None:
                    res.append(n)
            for n in ast.params:
                names = self.generatePossibleThunkNames(n, res)
                if names is None:
                    continue
                for it in names:
                    if it and it not in res:
                        res.append(it)
            return res
        elif isinstance(ast, AST_Name):
            return [ast._element]
        else:
            return res

    def all_data_available(self, name: Name) -> bool:
        """Check if all dependencies for a name are available
        :returns True if all dependencies are available
        :returns False if there are dependencies missing
        ":returns None: if name is not in list
        """
        e = self.active_thunk_table.get_entry_from_name(name)
        if e is None:
            return None

        for d in e.awaiting_data:
            if e.awaiting_data[d] is None:
                return False
        return True


    def get_cheapest_prepended_name(self, ast, dataset: ThunkTableEntry) -> (int, List):
        """prepend each name, find cheapest costs for the current layer
        :returns a touple of cost and name
        """
        function_names = self.optimizer._get_functions_from_ast(ast)
        data_names = self.optimizer._get_names_from_ast(ast)
        name_list = data_names + function_names
        cost = None
        for name in name_list:
            n = self.optimizer._set_prepended_name(ast, Name(name), ast)
            if n is None:
                continue
            entry_cost = dataset.awaiting_data.get(n)
            if entry_cost is None:
                continue
            if cost is None or cost[0] > entry_cost:
                cost = (entry_cost, n)
        return cost

    def compute_cost_and_requests(self, ast: AST, dataset: ThunkTableEntry) -> (int, List):
        """computes the cheapest costs and the way to achieve them
        :returns a tuple of the cost and the required requrests to achieve this costs"""
        if isinstance(ast, AST_FuncCall):
            overall_cost = self.get_cheapest_prepended_name(ast, dataset)
            function_cost = dataset.awaiting_data.get(ast._element)
            parameter_cost = []
            for p in ast.params:
                cost, requests = self.compute_cost_and_requests(p, dataset)
                parameter_cost.append((cost, requests))
            if function_cost is None:
                inner_cost = sys.maxsize
            else:
               inner_cost = function_cost + sum(list(map(lambda x: x[0], parameter_cost)))
            if overall_cost is None:
                overall_cost = (sys.maxsize, None)
            if inner_cost > overall_cost[0]:
                return overall_cost  #in this case, forwarding is the cheapest solution
            else:
                return (inner_cost, list(filter(lambda x: x is not None ,list(map(lambda x: x[1], parameter_cost)) + [ast._element])))
        elif isinstance(ast, AST_Name):
            cost = dataset.awaiting_data.get(ast._element)
            return (cost, ast._element)
        else:
            return (0, None)

    def isthunk(self, name: Name) -> bool:
        """ Check if a request is a thunk
        :returns True if it is a thunk request, else False"""
        if len(name.components) < 2 or name.components[-2] != b"THUNK":
            return False
        if name.components != b"NFN":
            return False
        return True
