"""NFN streaming executor for Named Functions written in Python"""

from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor

class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self):
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["checkStreaming"] = self.checkStreaming

    def checkStreaming(self, arg: str):
        if not arg:
            print("String is empty")
        elif arg.startswith("sdo:"):
            print("File for streaming")
            tmpList = arg.splitlines()
            tmpList.pop(0)
            for x in tmpList:
                if (self.checkForName(x)):
                    print(x + " : is a name")
                else:
                    print("This entry is not a name")
        else:
            print("File not for streaming")

    def checkForName(name: str):
        if name[0] != "/":
            return False
        else:
            return True