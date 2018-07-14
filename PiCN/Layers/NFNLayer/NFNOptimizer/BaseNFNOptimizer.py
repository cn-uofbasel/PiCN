"""Base class for the NFN Optimizers"""

import abc
from typing import Dict, List

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Packets import Interest


class BaseNFNOptimizer(object):
    """Base class for the NFN Optimizers"""

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable):
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self.faceidtable = faceidtable

    @abc.abstractmethod
    def required_data(self, prepended_prefix: Name, ast: AST) -> List[Name]:
        """decides which requests must be issued for the optimizer
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return List of names which should be requested
        """

    @abc.abstractmethod
    def compute_local(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:
        """decide if the computation should be executed locally
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return True if computation should be executed locally, else False
        """

    @abc.abstractmethod
    def compute_fwd(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:
        """decide if the computation should be forwarded
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return True if computation should be forwarded, else False
        """

    @abc.abstractmethod
    def rewrite(self, prepended_prefix: Name, ast: AST) -> List[str]:
        """rewrite the NFN interest. Creates a list of rewrites, ordered by priority. First is to be used first, others
        are backups, in case no result could be received using the first rewrite.
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return List of computation strings, including a marker which name should be prepended. List ordered by priority
        """

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
                # names.append(ast._element)
        return names

    def _get_functions_from_ast(self, ast: AST, names: Name = None):
        if names is None:
            names = []
        if isinstance(ast, AST_FuncCall):
            names.append(ast._element)
        if isinstance(ast, AST_FuncCall):
            for p in ast.params:
                names = self._get_functions_from_ast(p, names)
                # names.append(ast._element)
        return names
