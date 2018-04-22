"""Base Class for R2C Clients in PiCN's NFN Layer"""

import abc
from typing import List

from PiCN.Packets import Name

class BaseR2CClient(object):
    """Base Class for R2C Clients in PiCN's NFN Layer"""

    def __init__(self):
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
    def R2C_identify_Name(self, name: Name) -> bool:
        """checks if a R2C messages matches this handler
        :param name: Name to identify
        :return True if Name matches handler, else False
        """
