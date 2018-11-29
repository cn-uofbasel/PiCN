"""Executor for x86 Machine code. This Executor may be dangerous for the executing machine"""

import tempfile

from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor
from typing import List
from ctypes import *

class x86Executor(BaseNFNExecutor):
    """Executor for x86 Machine code. This Executor may be dangerous for the executing machine"""

    def __init__(self):
        self._language = "x86"

    def _get_entry_function_name(self, function: str) -> (str, str):
        pos1 = function.find(b'\n')
        header = function[:pos1]
        rest = function[pos1+1:]
        pos2 = rest.find(b'\n')
        entry_point_name = rest[:pos2]
        function_code = rest[pos2+1:]
        if header.decode () != self._language:
            return (None, None)
        return (entry_point_name.decode(), function_code)

    def execute(self, function_code: str, params: List):
        try:
            entry_function_name, program_code = self._get_entry_function_name(function_code)
            libfile = tempfile.NamedTemporaryFile()
            libfile.file.write(program_code)
            clib = CDLL(libfile.name)
            expr = 'clib.' + entry_function_name
            entry_point = eval(expr)
            if entry_point is None:
                print("function not found:", entry_function_name)
                return
            params_ready = []
            for p in params:
                if isinstance(p, str):
                    params_ready.append(p.encode())
                else:
                    params_ready.append(p)

            res = entry_point(*params_ready)
            libfile.close()
            return res
        except:
            print("error")
            # raise
            if libfile is not None:
                libfile.close()
            return None