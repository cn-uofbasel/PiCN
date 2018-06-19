"""Base class for the NFN Optimizers"""

import abc
from typing import Dict, List

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import AST
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable

class BaseNFNOptimizer(object):
    """Base class for the NFN Optimizers"""
    def __init__(self, data_structs: Dict):
        self._data_structs = data_structs

    @abc.abstractmethod
    def required_data(self, prepended_prefix: Name, ast: AST) -> List[Name]:
        """decides which requests must be issued for the optimizer
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return List of names which should be requested
        """

    @abc.abstractmethod
    def compute_local(self, prepended_prefix: Name, ast: AST) -> bool:
        """decide if the computation should be executed locally
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return True if computation should be executed locally, else False
        """

    @abc.abstractmethod
    def compute_fwd(self, prepended_prefix: Name, ast: AST) -> bool:
        """decide if the computation should be forwarded
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return True if computation should be forwarded, else False
        """

    @abc.abstractmethod
    def rewrite(self, prepended_prefix: Name, ast: AST) -> List[str]:
        """rewrite the NFN interest and prepend a name
        :param prepended_prefix: Prefix that was prepended to the interest
        :param ast: The Abstract Syntax Tree for the current computation
        :return List of computation strings, including a marker which name should be prepended.
        """

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

