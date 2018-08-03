"""Simple NFN Optimizer, for edge computing. Start computation at the edge and forward it in parallel"""

from typing import Dict

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Packets import Interest

class EdgeComputingOptimizer(BaseNFNOptimizer):

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidTable: BaseFaceIDTable) -> None:
        super().__init__(cs, fib, pit, faceidTable)

    def required_data(self, prepended_prefix: Name, ast: AST):
        return []

    def compute_local(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:

        if not isinstance(ast, AST_FuncCall): #only start if computation function local
            return False
        function_name = Name(ast._element)
        if not self.cs.find_content_object(function_name):
            return False #do not start computation

        pit = self.pit.get_container()
        pit_entry = self.pit.find_pit_entry(interest.name)
        if not pit_entry:
            return True
        faceid = pit_entry.faceids[0]
        addr_info = self.faceidtable.get_address_info(faceid)
        if "rsu" in addr_info.address and len(function_name.string_components) > 1 \
                and "id" not in function_name.string_components[1]:  #do not start computation if it comes form another RSU  #todo imporve this for ip
            return False
        return True

    def compute_fwd(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:

        pit_entry = self.pit.find_pit_entry(interest.name)
        if pit_entry:
            if self.fib.find_fib_entry(interest.name, pit_entry.fib_entries_already_used, pit_entry.face_id) is None:
                return False
        else:
            if self.fib.find_fib_entry(interest.name) is None:
                return False
        return True

    def rewrite(self, prepended_prefix: Name, ast: AST) -> List[str]:
        names = self._get_names_from_ast(ast)
        functions = self._get_functions_from_ast(ast)
        names_in_fib = []
        for n in names:
            if self.fib.find_fib_entry(Name(n), []):
                names_in_fib.append(Name(n))

        functions_in_fib = []
        for f in functions:
            if self.fib.find_fib_entry(Name(f), []):
                functions_in_fib.append(Name(f))

        rewrites = []
        for n in names_in_fib:
            rewrites.append(self._set_prepended_name(ast, n, ast))

        for f in functions_in_fib:
            rewrites.append(self._set_prepended_name(ast, f, ast))

        return rewrites
