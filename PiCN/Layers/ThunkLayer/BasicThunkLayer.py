"""This is the BasicThunk layer used to check if it is possible to compute a result, and determine the
cost of computing the result"""
import multiprocessing

from typing import List

from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList
from PiCN.Layers.RepositoryLayer.Repository import BaseRepository

class BasicThunkLayer(LayerProcess):

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable, parser: DefaultNFNParser, repo: BaseRepository=None, log_level=255):
        super().__init__("ThunkLayer", log_level)
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self.faceidtable = faceidtable
        self.parser = parser
        self.optimizer = BaseNFNOptimizer(self.cs, self.fib, self.pit, self.faceidtable)
        self.repo = repo
        self.running_computations = ThunkList()

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        packet_id = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            self.handleInterest(packet_id, packet)
        elif isinstance(packet, Content):
            self.handleContent(packet_id, packet)
        elif isinstance(packet, Nack):
            self.handleNack(packet_id, packet)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        to_lower.put(data)
        return

    def handleInterest(self, id: int, interest: Interest):

        data_size = self.get_data_size(interest.name)
        if data_size is not None:
            content = Content(interest.name, "DataSize:" + str(data_size))
            self.queue_to_lower.put(content)
            return

        if len(interest.name.components) < 2 or interest.name.components[-2] != b"THUNK":
            self.queue_to_higher.put([id, interest])
            return

        if interest.name.components != b"NFN":
            self.queue_to_higher.put([id, interest])
            return

        name = self.removeThunkMarker(interest.name)
        nfn_name = self.parser.network_name_to_nfn_str(name)
        ast = self.parser.parse(nfn_name)

        thunk_names = list(map(lambda x: self.addThunkMarker(self.parser.nfn_str_to_network_name(x)))
                           ,self.generatePossibleThunkNames(ast))

        self.running_computations.add_entry_to_thunk_table(name, id, thunk_names) #Create new computation
        for tn in thunk_names:
            data_size = self.get_data_size(tn)
            if data_size is not None:
                content = Content(interest.name, "DataSize:" + str(data_size))
                self.running_computations.add_estimated_cost_to_awaiting_data(name, data_size) #if data local -> set cost
                return
            interest = Interest(tn)
            self.queue_to_lower.put([id, interest])

        #TODO check if all costs are satified. if yes reply to main request
        #TODO find cheapest cost, cache plans

    def handleContent(self, id: int, content: Content):
        pass

        #TODO check if content is required
        #TODO find cheapest cost, cache plans (all required? how to find out if all are available)

    def handleNack(self, id: int, nack: Nack):
        pass
        #TODO Remove from required table

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

    def generatePossibleThunkNames(self, ast: AST, res: List = []) -> List:
        """Generate names that can be used for the planning"""
        if isinstance(ast, AST_FuncCall):
            name_list = self.optimizer._get_names_from_ast(ast)
            function_list = self.optimizer._get_functions_from_ast(ast)
            prepend_list = name_list + function_list
            fib_name_list = []
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
