"""Executor for x86 Machine code. This Executor may be dangerous for the executing machine
This Executor expects a NFN file as following:

x86
<entry point name>
<base64 encoded x86 library code as string>
"""

import tempfile
import base64

from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor
from typing import List
from ctypes import *

class x86Executor(BaseNFNExecutor):
    """Executor for x86 Machine code. This Executor may be dangerous for the executing machine"""

    def __init__(self):
        super().__init__()
        self._language = "x86"

    def _get_entry_function_name(self, function: str) -> (str, str):
        code_parts = function.split('\n', 2)
        if len(code_parts) != 3:
            return (None, None)
        if code_parts[0] != self._language:
            return (None, None)
        functionname = code_parts[1]
        code = code_parts[2]
        code = base64.urlsafe_b64decode(code)
        return (functionname, code)

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
                #libfile.close()
                return None
            params_ready = []
            for p in params:
                if isinstance(p, str):
                    params_ready.append(p.encode())
                else:
                    params_ready.append(p)
            res = entry_point(*params_ready)
            #libfile.close()
            return res
        except Exception as e:
            print(e.with_traceback())
            # raise
            return None
