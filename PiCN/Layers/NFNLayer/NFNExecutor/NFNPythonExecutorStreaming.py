"""NFN streaming executor for Named Functions written in Python"""

import multiprocessing

from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor

class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self):#, queue_to_lower, queue_from_lower):
        self._language = "PYTHONSTREAM"
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["checkStreaming"] = self.checkStreaming
        self._sandbox["getNext"] = self.getNext
        self._sandbox["print"] = print
        self.nameList = []
        self.posNameList = 0
        self.queue_to_lower = multiprocessing.Queue
        self.queue_from_lower = multiprocessing.Queue
        #print (self._sandbox)

    # Setter function to set both queues after the forwarders being initialized
    def setQueues(self, queue_to_lower: multiprocessing.Queue, queue_from_lower: multiprocessing.Queue):
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        #print(self.queue_to_lower)

    def getNext(self, arg: str, amount: int):
        self.nameList = arg.splitlines()
        self.nameList.pop(0)
        toDo = self.nameList.copy()
        print(self.nameList)
        self.posNameList = amount
        for i in range (0, self.posNameList):
            self.queue_to_lower.put(toDo.pop(i))
            print(self.queue_from_lower.get())
        return 0

    # Checks if file is for streaming and lines start with a '/'
    def checkStreaming(self, arg: str):
        # Check if String is empty
        if not arg:
            return False
        # Check if streaming prefix is available
        elif arg.startswith("sdo:"):
            print("File is for streaming")
            tmpList = arg.splitlines()
            tmpList.pop(0)
            for x in tmpList:
                if self.checkForName(x) is False:
                    return False
            return True
        # Wrong prefix, file is not for streaming
        else:
            return False

    # Helper function to check if the string starts with '/'
    def checkForName(self, name: str):
        if name[0] == "/":
            return True
        else:
            return False