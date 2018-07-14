"""Base class for the NFN Executor"""

import abc
from typing import List

class BaseNFNExecutor(object):

    def __init__(self):
        self._language = ""
        pass

    @property
    def language(self) -> str:
        """returns the language type supported by the executor
        :return string identifying the language the Executor can handle
        """
        return  self._language

    @abc.abstractmethod
    def execute(self, function_code: str, params: List) -> str: #TODO params no string? ast value! same for result?
        """execute a function code. this can call other programming languages
        IMPORTANT: SANDBOXING REQUIRED!!!
        :param function_code: function code as str
        :param params: list containing the parameter
        :return result as string
        """