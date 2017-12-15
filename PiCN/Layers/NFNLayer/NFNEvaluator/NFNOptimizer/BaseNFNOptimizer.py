"""Base class for the NFN Optimizers"""

import abc

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import AST
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable

class BaseNFNOptimizer(object):
    """Base class for the NFN Optimizers"""
    def __init__(self, prefix: Name, cs: BaseContentStore, fib: BaseForwardingInformationBase,
                 pit: BasePendingInterestTable):
        self.prefix: Name = prefix
        self._cs: BaseContentStore = cs
        self._fib: BaseForwardingInformationBase = fib
        self._pit: BasePendingInterestTable = pit

    @abc.abstractclassmethod
    def compute_local(self, ast: AST) -> bool:
        """decide if the computation should be executed locally"""

    @abc.abstractclassmethod
    def compute_fwd(self, ast: AST) -> bool:
        """decide if the computation should be forwarded"""

    @abc.abstractclassmethod
    def rewrite(self, ast: AST):
        """rewrite the NFN interest and prepend a name"""

    @property
    def cs(self):
        return self._cs

    @cs.setter
    def cs(self, cs):
        self._cs = cs

    @property
    def fib(self):
        return self._fib

    @fib.setter
    def fib(self, fib):
        self._fib = fib

    @property
    def pit(self):
        return self._pit

    @pit.setter
    def pit(self, pit):
        self._pit = pit

