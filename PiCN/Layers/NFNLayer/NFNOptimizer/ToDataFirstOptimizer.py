"""Simple NFN Optimizer, alsways forwarding towards data"""

from typing import Dict

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer


class ToDataFirstOptimizer(BaseNFNOptimizer):

    def __init__(self, prefix: Name, data_structs: Dict) -> None:
        super().__init__(prefix, data_structs)

    def compute_local(self, ast: AST) -> bool:
        if self.cs.find_content_object(self.prefix):
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

    def compute_fwd(self, ast: AST) -> bool:
        if self.cs.find_content_object(self.prefix):
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

    def rewrite(self, ast: AST):
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


    def _set_prepended_name(self, ast: AST, name: Name, root: AST):
        if isinstance(ast, AST_FuncCall) or isinstance(ast, AST_Name):
            if name == Name(ast._element):
                ast._prepend = True
                res = str(root)
                ast._prepend = False
                return res
        if isinstance(ast, AST_FuncCall):
            for p in ast.params:
                res = self._set_prepended_name(p, name, root)
                if res is not None:
                    return res
        return None

    def _get_names_from_ast(self, ast: AST, names: Name = None):
        if names is None:
            names = []
        if isinstance(ast, AST_Name):
            names.append(ast._element)
        if isinstance(ast, AST_FuncCall):
            for p in ast.params:
                names = self._get_names_from_ast(p, names)
            #names.append(ast._element)
        return names

    def _get_functions_from_ast(self, ast: AST, names: Name = None):
        if names is None:
            names = []
        if isinstance(ast, AST_FuncCall):
            names.append(ast._element)
        if isinstance(ast, AST_FuncCall):
            for p in ast.params:
                names = self._get_functions_from_ast(p, names)
            #names.append(ast._element)
        return names