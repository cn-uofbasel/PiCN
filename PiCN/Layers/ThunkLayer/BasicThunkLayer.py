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

class BasicThunkLayer(LayerProcess):

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable, parser: DefaultNFNParser, log_level=255):
        super().__init__("ThunkLayer", log_level)
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self.faceidtable = faceidtable
        self.parser = parser

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
        if len(interest.name.components) < 2 or interest.name.components[-2] != b"THUNK":
            self.queue_to_higher.put([id, interest])
            return

        if interest.name.components != b"NFN":
            self.queue_to_higher.put([id, interest])
            return

        name = self.removeThunkMarker(interest.name)
        nfn_name = self.parser.network_name_to_nfn_str(name)
        ast = self.parser.parse(nfn_name)



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

    def generatePossibleThunkNames(self, ast: AST, res: List) -> List:
        """Generate names that can be used for the planning"""
        if isinstance(ast, AST_FuncCall):
            fib_entry = self.fib.find_fib_entry(ast._element)
            if fib_entry:
                ast._prepend = True
                n = str(ast)
                ast._prepend = False
                if n not in res:
                    res.append(n)
            for p in ast.params:
                n = self.generatePossibleThunkNames(p, res)
                if n is not None and n not in res:
                    res.append(n)
            return res
        elif isinstance(ast, AST_Name):
            fib_entry = self.fib.find_fib_entry(ast._element)
            if fib_entry:
                ast._prepend = True
                n = str(ast)
                ast._prepend = False
                if n not in res:
                    res.append(n)
                return res
        else:
            return None
