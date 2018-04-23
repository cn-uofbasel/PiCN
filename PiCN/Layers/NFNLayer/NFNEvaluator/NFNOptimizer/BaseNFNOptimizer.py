"""Base class for the NFN Optimizers"""

import abc
from typing import Dict

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import AST
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable

class BaseNFNOptimizer(object):
    """Base class for the NFN Optimizers"""
    def __init__(self, prefix: Name, data_structs: Dict):
        self.prefix: Name = prefix
        self._data_structs = data_structs

    @abc.abstractmethod
    def compute_local(self, ast: AST) -> bool:
        """decide if the computation should be executed locally"""

    @abc.abstractmethod
    def compute_fwd(self, ast: AST) -> bool:
        """decide if the computation should be forwarded"""

    @abc.abstractmethod
    def rewrite(self, ast: AST):
        """rewrite the NFN interest and prepend a name"""

    @property
    def cs(self):
        return self._data_structs.get('cs')

    @cs.setter
    def cs(self, cs):
        self._data_structs['cs'] = cs

    @property
    def fib(self):
        return self._data_structs.get('fib')

    @fib.setter
    def fib(self, fib):
        self._data_structs['fib'] = fib

    @property
    def pit(self):
        return self._data_structs.get('pit')

    @pit.setter
    def pit(self, pit):
        self._data_structs['pit'] = pit
