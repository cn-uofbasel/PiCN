"""NFN executor for Named Functions written in Python"""

from typing import List
from types import FunctionType, CodeType

from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor
from PiCN.Demos.MapDetection.MapDetection import map_detection

class NFNPythonExecutor(BaseNFNExecutor):

    def __init__(self):
        self._language = "PYTHON"
        self._sandbox = self._init_sandbox()

    def execute(self, function_code: str, params: List):
        try:
            entry_function_name, program_code = self._get_entry_function_name(function_code)
            if entry_function_name is None or program_code is None:
                return None
            machine_code = compile(program_code, '', 'exec')
            if machine_code is None:
                return None
            entry_point = None
            lib_functions = []
            for fcode in machine_code.co_consts:
                if isinstance(fcode, CodeType):
                    if fcode.co_name == entry_function_name:
                        entry_point = FunctionType(fcode, self._sandbox)
                    else:
                        lib_functions.append((fcode.co_name, FunctionType(fcode, self._sandbox)))
            if entry_point is None:
                return None
            for lf in lib_functions: #enable calling of all functions but not the entry point
                if lf[1] is None:
                    continue
                self._sandbox[lf[0]] = lf[1]
            return entry_point(*params)
        except:
            #raise
            return None

    def _get_entry_function_name(self, function: str) -> (str, str):
        code_parts = function.split('\n', 2)
        if len(code_parts) != 3:
            return (None, None)
        if code_parts[0] != self._language:
            return (None, None)
        functionname = code_parts[1]
        code = code_parts[2]
        return (functionname, code)

    def _init_sandbox(self):
        return {
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "float": float,
            "object": object,
            "bool": bool,
            # "callable": callable,  #TODO Check that
            "True": True,
            "False": False,
            #"dir": dir, #TODO Check that
            "frozenset": frozenset,
            #"getattr": getattr, #TODO Check that
            #"hasattr": hasattr,  #TODO Check that
            "abs": abs,
            "complex": complex,
            "divmod": divmod,
            "id": id,
            "pow": pow,
            "round": round,
            "slice": slice,
            "vars": vars,
            "hash": hash,
            "hex": hex,
            "int": int,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "len": len,
            "map": map,
            "filter": filter,
            "max": max,
            "min": min,
            "oct": oct,
            "chr": chr,
            "ord": ord,
            "range": range,
            "repr": repr,
            "str": str,
            "type": type,
            "zip": zip,
            "None": None,
            "map_detection": map_detection,
            }
