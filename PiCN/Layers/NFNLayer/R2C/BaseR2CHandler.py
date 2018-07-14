"""Base Class for R2C Clients in PiCN's NFN Layer"""

import abc
from typing import List

from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Packets import Name, Content


class BaseR2CHandler(object):
    """Base Class for R2C Clients in PiCN's NFN Layer"""

    def __init__(self, parser: DefaultNFNParser = DefaultNFNParser()):
        self.parser = parser
        pass

    @abc.abstractmethod
    def R2C_selection(self, names: List[Name]) -> List[Name]:
        """selects for which of the timeouted data should be handled
        :param names: list of names to select from
        :return filtered list of names, empty list of none of the entries requires a refresh, None if comp failed
        """

    @abc.abstractmethod
    def R2C_handle_reply(self, name: Name):
        """handle a R2C reply
        :param name: name of the R2C request
        """

    @abc.abstractmethod
    def R2C_create_message(self, name: Name) -> Name:
        """create an R2C message that corresponds to a name
        :param name: name that should be transformed to corresponding R2C
        :return R2C name
        """

    @abc.abstractmethod
    def R2C_get_original_message(self, name: Name) -> Name:
        """takes a R2C message and removes the R2C components
        :param name: R2C name from which the components should be removed
        :return NFN name without R2C marker
        """

    @abc.abstractmethod
    def R2C_identify_Name(self, name: Name) -> bool:
        """checks if a R2C messages matches this handler
        :param name: Name to identify
        :return True if Name matches handler, else False
        """

    @abc.abstractmethod
    def R2C_handle_request(self, name: Name, computationTable: BaseNFNComputationTable) -> Content:
        """handles a R2C request
        :param Name: Name of the R2C request
        :param computationTable: The current computationTable
        :return content object to reply
        """
