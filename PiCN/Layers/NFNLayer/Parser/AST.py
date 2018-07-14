"""Elements for the Abstract Syntax Tree for NFN"""

from typing import List

from PiCN.Packets import Name


class AST(object):
    """Abstract AST element"""

    def __init__(self, element: str, prependmarker: str = "%"):
        self._element: str = element
        self._prepend: bool = False
        self._prependmarker = prependmarker

    def __str__(self):
        if self._prepend:
            return self._prependmarker + self._element + self._prependmarker
        else:
            return self._element

    @property
    def type(self):
        return AST


class AST_FuncCall(AST):
    """FuncCall AST Element"""

    def __init__(self, element: str, prependmarker: str = "%"):
        super().__init__(element.replace("(", ""), prependmarker="%")
        self.params: List[AST] = []

    def add_param(self, param: AST):
        self.params.append(param)

    def __str__(self):
        if self._prepend:
            res = self._prependmarker + self._element + self._prependmarker + "("
        else:
            res = self._element + "("
        for p in self.params:
            res += str(p)
            if p is not self.params[-1]:
                res += ","
        return res + ")"

    @property
    def type(self):
        return AST_FuncCall


class AST_Name(AST):
    """Name AST Element"""

    def __init__(self, element: str):
        super().__init__(element)

    @property
    def type(self):
        return Name


class AST_String(AST):
    """String AST Element"""

    def __init__(self, element: str):
        super().__init__(element[1:-1])  # removes "

    def __str__(self):
        return '"' + self._element + '"'

    @property
    def type(self):
        return str


class AST_Int(AST):
    """Int AST Element"""

    def __init__(self, element: str):
        super().__init__(element)

    @property
    def type(self):
        return int


class AST_Float(AST):
    """Float AST Element"""

    def __init__(self, element: str):
        super().__init__(element)

    @property
    def type(self):
        return float


class AST_Var(AST):
    """Var AST Element"""

    def __init__(self, element: str):
        super().__init__(element)

    @property
    def type(self):
        return AST_Var
