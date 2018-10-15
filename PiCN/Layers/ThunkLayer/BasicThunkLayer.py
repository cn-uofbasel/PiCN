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

class BasicThunkLayer(LayerProcess):

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable, parser: DefaultNFNParser, log_level=255):
        super().__init__("ThunkLayer", log_level)
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self.faceidtable = faceidtable
        self.parser = parser
        self.optimizer = BaseNFNOptimizer(self.cs, self.fib, self.pit, self.faceidtable)
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
        #TODO what about local function, data, use info from meta data?
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

        self.running_computations.add_entry_to_thunk_table(name, id, thunk_names)
        for tn in thunk_names:
            interest = Interest(thunk_names)
            self.queue_to_lower.put([id, interest])


        #TODO parse interest -> ast
        #TODO create possible requests
        #TODO find cheapest cost, cache plans

    def handleContent(self, id: int, content: Content):
        pass

    def handleNack(self, id: int, nack: Nack):
        pass


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





