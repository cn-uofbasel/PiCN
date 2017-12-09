"""Default Parser for NFN"""

from typing import Dict

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import TokenType
from PiCN.Layers.NFNLayer.Parser import Token
from PiCN.Layers.NFNLayer.Parser import DefaultNFNTokenizer

from PiCN.Layers.NFNLayer.Parser.AST import *


class DefaultNFNParser(object):
    """Default Parser for NFN"""

    def __init__(self):
        """Default Parser for NFN"""
        self.stringToken = Token(TokenType.STRING, '"', "[A-Za-z0-9]", '"')
        self.intToken = Token(TokenType.INT, '[0-9\+\-]', "[0-9]", '[0-9]')
        self.floatToken = Token(TokenType.FLOAT, '[0-9\+\-]', "[0-9.Ee]", '[0-9]')
        self.nameToken = Token(TokenType.NAME, "/", "[A-Za-z0-9/]", "[A-Za-z0-9]")
        self.varToken = Token(TokenType.VAR, "[A-Za-z0-9]", "[A-Za-z0-9]", "[A-Za-z0-9]")
        self.funcToken = Token(TokenType.FUNCCALL, "/", "[A-Za-z0-9/]", "\(")
        self.endFuncToken = Token(TokenType.ENDFUNCCALL, "\)", "", "")
        self.paramSeparator = Token(TokenType.PARAMSEPARATOR, ",", "", "")

        self.tokenizer = DefaultNFNTokenizer()
        self.tokenizer.add_token(self.stringToken)
        self.tokenizer.add_token(self.intToken)
        self.tokenizer.add_token(self.floatToken)
        self.tokenizer.add_token(self.nameToken)
        self.tokenizer.add_token(self.varToken)
        self.tokenizer.add_token(self.funcToken)
        self.tokenizer.add_token(self.endFuncToken)
        self.tokenizer.add_token(self.paramSeparator)

        self.tokenToAst:Dict[TokenType, type(AST)] = {}
        self.tokenToAst[TokenType.STRING] = AST_String
        self.tokenToAst[TokenType.INT] = AST_Int
        self.tokenToAst[TokenType.FLOAT] = AST_Float
        self.tokenToAst[TokenType.NAME] = AST_Name
        self.tokenToAst[TokenType.VAR] = AST_Var
        self.tokenToAst[TokenType.FUNCCALL] = AST_FuncCall
        self.tokenToAst[TokenType.ENDFUNCCALL] = None
        self.tokenToAst[TokenType.PARAMSEPARATOR] = None

    def parse(self, string: str) -> AST:
        """Take a string and create an AST"""

        tokens = self.tokenizer.tokenize(string)

        depth = 0
        root = None
        for token in tokens:
            tokentype = token[0]
            tokenstr = token[1]
            if tokentype not in self.tokenToAst:
                return None
            ast_element_t = self.tokenToAst[tokentype]
            if ast_element_t is not None:
                ast_element = ast_element_t(tokenstr)
                if root is None:
                    root = ast_element
                else:
                    cur_element = root
                    for i in range(1, depth):
                        cur_element = cur_element.params[-1]
                    if not isinstance(cur_element, AST_FuncCall):
                        return None #Syntax error
                    cur_element.add_param(ast_element)

            if tokentype == TokenType.FUNCCALL:
                depth+=1
            if tokentype == TokenType.ENDFUNCCALL:
                depth-=1
        if depth != 0:
            return None #Syntax error
        return root

    def network_name_to_nfn_str(self, name: Name) -> str:
        if len(name.components) == 2:
            return name.components[1], None
        if name.components [-1] != "NFN":
            return None, None
        prepended_name = Name()
        prepended_name.components = name.components[:-2]
        nfn_comp = name.components[-2].replace("_", prepended_name.to_string())
        nfn_comp = nfn_comp.replace("\\", "/")
        return  nfn_comp, prepended_name

    def nfn_str_to_network_name(self, nfn_str: str, prependmarker: str = "%") -> Name:
        if prependmarker not in nfn_str:
            return None
        comps = nfn_str.split(prependmarker)
        nfn_comp = comps[0] + "_" + comps[2]
        name = Name(comps[1])
        name.components.append(nfn_comp)
        name.components.append("NFN")
        return name



