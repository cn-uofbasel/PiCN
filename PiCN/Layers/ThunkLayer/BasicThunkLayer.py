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
            self.logger.debug("Handle interest: " + str(packet.name))
            self.handleInterest(packet_id, packet, from_higher=False)
        elif isinstance(packet, Content):
            self.logger.debug("Handle content: " + str(packet.name) + " | " + str(packet.content))
            self.handleContent(packet_id, packet, from_higher=False)
        elif isinstance(packet, Nack):
            self.logger.debug("Handle nack: " + str(packet.name))
            self.handleNack(packet_id, packet, from_higher=False)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        to_lower.put(data)
        return

    def handleInterest(self, id: int, interest: Interest, from_higher):

        if not self.isthunk(interest.name):
            if from_higher:
                self.queue_to_lower.put([id, interest])
                return
            else:
                self.queue_to_higher.put([id, interest])
            return

        if interest.name.components[-1] == b'THUNK':
            data_size = self.get_data_size(self.removeThunkMarker(interest.name))
            if data_size is not None:
                content = Content(self.addThunkMarker(interest.name), str(data_size))
                self.queue_to_lower.put([id, content])
                return

        name = self.removeThunkMarker(interest.name)
        nfn_str, prepended_name = self.parser.network_name_to_nfn_str(name)
        ast = self.parser.parse(nfn_str)

        thunks = self.generatePossibleThunkNames(ast)
        self.logger.info("THUNKNAMES: "+ str(thunks))
        thunk_names = []

        for t in thunks:
            if '(' in t and ')' in t:
                n = self.parser.nfn_str_to_network_name(t)
            else:
                n = Name(t)
            thunk_names.append(n)

        self.active_thunk_table.add_entry_to_thunk_table(name, id, thunk_names) #Create new computation
        for tn in thunk_names:
            data_size = self.get_data_size(self.removeThunkMarker(tn))
            if data_size is not None:
                #content = Content(interest.name, str(data_size))
                #self.queue_to_lower.put([id, content])
                self.active_thunk_table.add_estimated_cost_to_awaiting_data(tn, 0)#data_size) #if data local -> set cost to 0
                continue
            interest = Interest(self.addThunkMarker(tn))
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
        self.active_thunk_table.add_estimated_cost_to_awaiting_data(self.removeThunkMarker(content.name), cost)
        self.check_and_compute_cost()

    def check_and_compute_cost(self):
        """check if all data are available and start computation"""
        removes = []
        for e in self.active_thunk_table.get_container():
            if self.all_data_available(e.name):
                name = self.removeThunkMarker(e.name)
                nfn_str, prepended_name = self.parser.network_name_to_nfn_str(name)
                ast = self.parser.parse(nfn_str)
                cost, path = self.compute_cost_and_requests(ast, e)
                self.planTable.add_plan(e.name, path, cost)
                removes.append(e)
                if cost != sys.maxsize:
                    content = Content(self.addThunkMarker(e.name), str(cost))
                    self.queue_to_lower.put([e.id, content])
                else:
                    nack = Nack(self.addThunkMarker(e.name), NackReason.COMP_PARAM_UNAVAILABLE, Interest(self.addThunkMarker(e.name)))
                    self.queue_to_lower.put([e.id, nack])
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
        for e in self.active_thunk_table.get_container(): #remove entrys which cannot be solved anymore
            if len(self.active_thunk_table.get_entry_from_name(e.name).awaiting_data) == 0:
                removes.append(e)
            self.check_and_compute_cost()
        for e in removes:
            self.active_thunk_table.remove_entry_from_thunk_table(e.name)
            nack = Nack(e.name, NackReason.NO_ROUTE, Interest(e.name))
            self.queue_to_lower.put([e.id, nack])


    def get_data_size(self, name: Name) -> int:
        if self.cs is not None:
            cs_entry = self.cs.find_content_object(name) #if content is available local in CS, use it
        else:
            cs_entry = None
        data_size = None
        if cs_entry is not None:
            if cs_entry.content.content.startswith("mdo:"):
                entry_splits = cs_entry.content.content.split(":")
                if len(entry_splits) > 2:
                    data_size = int(entry_splits[1])
            else:
                data_size = len(cs_entry.content.content)
        elif self.repo is not None:
            if self.repo.is_content_available(name):
                data_size = self.repo.get_data_size(name)
        return data_size

    def removeThunkMarker(self, name: Name) -> Name:
        """Remove the Thunk Marker from a Name"""
        ret = Name(name.components[:])
        if len(name.components) > 1 and name.components[-1] == b'THUNK':
            del ret.components[-1]
            return ret
        if len(name.components) < 2 or name.components[-2] != b"THUNK":
            return name
        del ret.components[-2]
        return ret

    def addThunkMarker(self, name: Name) -> Name:
        """Add a thunk marker to a Name"""
        ret = Name(name.components[:])
        if name.components[-1] == b'THUNK':
            return name
        if name.components[-1] != b"NFN":
            ret += "THUNK"
            return ret
        if len(name.components) < 2 or name.components[-2] == b"THUNK":
            return name
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
            if self.fib.find_fib_entry(Name(ast._element)) or self.cs.find_content_object(Name(ast._element)):
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
            if '(' in n or ')' in n:
                n = self.parser.nfn_str_to_network_name(n)
            else:
                n = Name(n)
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
            function_cost = dataset.awaiting_data.get(Name(ast._element))
            parameter_cost = []
            for p in ast.params:
                cost, requests = self.compute_cost_and_requests(p, dataset)
                parameter_cost.append((cost, requests))
            if function_cost is None:
                inner_cost = sys.maxsize
            else:
                try:
                    inner_cost = function_cost + sum(list(map(lambda x: x[0], parameter_cost)))
                except:
                    inner_cost = sys.maxsize
            if overall_cost is None:
                overall_cost = (sys.maxsize, None)
            if inner_cost > overall_cost[0]:
                return overall_cost  #in this case, forwarding is the cheapest solution
            else:
                return (inner_cost, list(filter(lambda x: x is not None ,list(map(lambda x: x[1], parameter_cost)) + [Name(ast._element)])))
        elif isinstance(ast, AST_Name):
            cost = dataset.awaiting_data.get(Name(ast._element))
            return (cost, Name(ast._element))
        else:
            return (0, None)

    def isthunk(self, name: Name) -> bool:
        """ Check if a request is a thunk
        :returns True if it is a thunk request, else False"""
        if len(name.components) > 1 and name.components[-1] == b"THUNK":
            return True
        if len(name.components) < 2 or name.components[-2] != b"THUNK":
            return False
        if name.components[-1] != b"NFN":
            return False
        return True
