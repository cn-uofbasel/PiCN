"""Tokenizer for NFN expressions
    * Define startpattern, valied pattern and stop patten to parse a token
    * always uses the longest possible pattern
    * to single char pattern has no token and stop pattern, both must be ""
"""

import re
import _sre
from enum import Enum
from typing import List, Tuple

class TokenType(Enum):
    NONE = 1,
    FUNCCALL = 2,
    ENDFUNCCALL = 3,
    PARAMSEPARATOR = 4,
    NAME = 5,
    INT = 6,
    FLOAT = 7,
    STRING = 8,
    VAR = 9,


class Token(object):
    """A Token for the NFN Tokenizer"""

    def __init__(self, type: TokenType, startChars:str, tokens:str, stopChars:str):
        self._startChars: _sre.SRE_Pattern = re.compile(startChars)
        self._tokens: _sre.SRE_Pattern = re.compile(tokens)
        self._stopChars: _sre.SRE_Pattern = re.compile(stopChars)
        self._type: TokenType = type

        if tokens == "":
            self._tokens = None
        if stopChars == "":
            self._stopChars = None

    def getToken(self, input) -> (TokenType, str):
        res: str = ""
        if len(input) < 1 or not self._startChars.match(input[0]):
            return (TokenType.NONE, "")
        res = res + input[0]
        if len(input) > 1:
            input = input[1:]
        for i in input:
            if self._tokens and self._tokens.match(i):
                res = res + i
            elif self._stopChars and self._stopChars.match(i):
                res = res + i
                return self.verifyStartEnd(res)
            else:
                return self.verifyStartEnd(res)
        return self.verifyStartEnd(res)

    def verifyStartEnd(self, string: str):
        if self._startChars.match(string[0]) and not self._stopChars and len(string) == 1:
            return (self._type, string)
        if self._startChars.match(string[0]) and self._stopChars.match(string[-1]):
            return (self._type, string)
        else:
            return (TokenType.NONE, "")

class DefaultNFNTokenizer(object):
    """Default NFN Tokenizer"""

    def __init__(self):
        self._tokens: List[Token] = []
        self.empty_tokens = re.compile("[\(\"]")

    def add_token(self, token: Token):
        """Add a Token to the Token-List"""
        self._tokens.append(token)

    def tokenize(self, input: str) -> List[Tuple[TokenType, str]]:
        """Tokenize a given String"""
        res = []
        cur_string = input
        max_iterations = len(input)
        while cur_string is not "" and max_iterations > 0:
            ts = []
            for token in self._tokens:
                ts.append(token.getToken(cur_string))
            res_tok = max(ts, key=lambda t: len(t[1]))
            if res_tok[0] == TokenType.NONE or res_tok[1] == "":
                return None
            res.append(res_tok)
            cur_string = cur_string[len(res_tok[1]):]
            --max_iterations
        return res
