"""Simple NFN Optimizer, alsways forwarding towards data"""

from typing import Dict

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer


class ToDataFirstOptimizer(BaseNFNOptimizer):

    def __init__(self, data_structs: Dict) -> None:
        super().__init__(data_structs)

    def required_data(self, prepended_prefix: Name, ast: AST):
        return []

    def compute_local(self, prepended_prefix: Name, ast: AST) -> bool:
        if self.cs.find_content_object(prepended_prefix):
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

    def compute_fwd(self, prepended_prefix: Name, ast: AST) -> bool:
        if prepended_prefix is None:
            names = self._get_functions_from_ast(ast)
            if names != []:
                prepended_prefix = names[0]
        if self.cs.find_content_object(prepended_prefix):
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

        return rewrites


    def _set_prepended_name(self, ast: AST, name: Name, root: AST) -> str:
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