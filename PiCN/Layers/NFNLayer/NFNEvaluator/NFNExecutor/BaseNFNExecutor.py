"""Base class for the NFN Executor"""

import abc
from typing import List

class BaseNFNExecutor(object):

    def __init__(self):
        self._language = ""
        pass

    @property
    def language(self):
        """returns the language type supported by the executor"""
        return  self._language

    @abc.abstractclassmethod
    def execute(self, function: str, params: List) -> str: #TODO params no string? ast value! same for result?
        """execute a function code. this can call other programming languages
        IMPORTANT: SANDBOXING REQUIRED!!!
        """