"""Simple NFN Optimizer, always forwarding towards data"""

from typing import Dict

from PiCN.Packets import Interest
from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable

class MapReduceOptimizer(BaseNFNOptimizer):

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable) -> None:
        super().__init__(cs, fib, pit, faceidtable)

    def required_data(self, prepended_prefix: Name, ast: AST):
        return []

    def compute_local(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:
        if self.cs.find_content_object(prepended_prefix):
            return True
        if self.check_ast_params_against_fib_for_multiple_pathes(ast):
            return True
        names = self._get_names_from_ast(ast)
        functions = self._get_functions_from_ast(ast)
        names_in_fib = []
        for n in names:
            if self.fib.find_fib_entry(Name(n), []):
                names_in_fib.append(Name(n))

        functions_in_fib = []
        for f in functions:
            if self.fib.find_fib_entry(Name(f), []):
                names_in_fib.append(Name(f))

        if len(names_in_fib) > 0 or len(functions_in_fib) > 0:
            return False
        return True

    def compute_fwd(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:
        if prepended_prefix is None:
            names = self._get_functions_from_ast(ast)
            if names != []:
                prepended_prefix = names[0]
        if self.cs.find_content_object(prepended_prefix):
            return False
        if self.check_ast_params_against_fib_for_multiple_pathes(ast):
            return False
        names = self._get_names_from_ast(ast)
        functions = self._get_functions_from_ast(ast)
        names_in_fib = []
        for n in names:
            if self.fib.find_fib_entry(Name(n), []):
                names_in_fib.append(Name(n))

        functions_in_fib = []
        for f in functions:
            if self.fib.find_fib_entry(Name(f), []):
                names_in_fib.append(Name(f))

        if len(names_in_fib) == 0 and len(functions_in_fib) == 0:
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

        rewrites.append('local')
        return rewrites

    def check_ast_params_against_fib_for_multiple_pathes(self, ast: AST) -> bool:
        if not isinstance(ast, AST_FuncCall):
            return False
        params = ast.params
        if len(params) < 2:
            return False
        faceids = []
        for p in params:
            if p.type == Name:
                entry = self.fib.find_fib_entry(Name(p._element))
                for ef in entry.faceid:
                    if ef not in faceids:
                        faceids.append(ef)
        if len(faceids) > 2:
            return True
        return False


