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

        pit = self.pit.get_container()
        pit_entry = self.pit.find_pit_entry(interest.name)
        if not pit_entry:
            return True
        faceid = pit_entry.faceids[0]
        addr_info = self.faceidtable.get_address_info(faceid)
        if "rsu" in addr_info.address:
            return False
        return True

    def compute_fwd(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:
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
