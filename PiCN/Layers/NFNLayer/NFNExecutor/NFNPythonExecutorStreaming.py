"""NFN streaming executor for Named Functions written in Python"""

from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor

class NFNPythonExecutorStreaming(NFNPythonExecutor):
    pass

    def __init__(self):
        self._sandbox = super._init_sandbox()
        self._sandbox["checkStreaming"] = self.checkStreaming

    def checkStreaming(self, arg: str):
        if not arg:
            print("String is empty")
        elif arg[0:4] == "sdo:":
            print("File for streaming")
            if (self.checkForName(arg[5:])):
                print("File contains name")
        else:
            print("File not for streaming")

    def checkForName(self, name: str):
        if name[0] != "/":
            return False
        else:
            return True