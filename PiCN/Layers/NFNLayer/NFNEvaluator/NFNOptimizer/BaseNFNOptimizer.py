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
        self.cs: BaseContentStore = cs
        self.fib: BaseForwardingInformationBase = fib
        self.pit: BasePendingInterestTable = pit

    @abc.abstractclassmethod
    def compute_local(self, ast: AST) -> bool:
        """decide if the computation should be executed locally"""

    @abc.abstractclassmethod
    def compute_fwd(self, ast: AST) -> bool:
        """decide if the computation should be forwarded"""

    @abc.abstractclassmethod
    def rewrite(self, ast: AST):
        """rewrite the NFN interest and prepend a name"""