"""NFN streaming executor for Named Functions written in Python"""

from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor

class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self, queue_to_lower, queue_from_lower):
        self._language = "PYTHONSTREAM"
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["checkStreaming"] = self.checkStreaming
        self._sandbox["getNext"] = self.getNext
        self._sandbox["print"] = print
        self._nameList = []
        self._posNameList = 0 
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        #print (self._sandbox)

    def getNext(self, amount: int):

        return 0

    def checkStreaming(self, arg: str):
        # Check if String is empty
        if not arg:
            # print("String is empty")
            return False
        # Check if streaming prefix is available
        elif arg.startswith("sdo:"):
            print("File is for streaming")
            tmpList = arg.splitlines()
            tmpList.pop(0)
            for x in tmpList:
                if self.checkForName(x) is False:
                    # print(x + " : is not a name")
                    return False
            return True
        # Wrong prefix, file is not for streaming
        else:
            #print("File not for streaming")
            return False

    def checkForName(self, name: str):
        if name[0] == "/":
            return True
        else:
            return False