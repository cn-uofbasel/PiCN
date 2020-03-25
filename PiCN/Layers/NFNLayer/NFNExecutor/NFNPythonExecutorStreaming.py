"""NFN streaming executor for Named Functions written in Python"""

import multiprocessing


from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Packets import Interest, Content


class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self):  # , queue_to_lower, queue_from_lower):
        self._language = "PYTHONSTREAM"
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["checkStreaming"] = self.checkStreaming
        self._sandbox["getNext"] = self.getNext
        self._sandbox["print"] = print
        self.nameList: list = None
        self.posNameList: int = None
        self.queue_to_lower: multiprocessing.Queue = None
        self.queue_from_lower: multiprocessing.Queue = None
        self.computation_table: NFNComputationList = None
        self.packetID : int = None
        # self.computation_table = NFNComputationList
        # print (self._sandbox)

    # Setter function to set both queues after the forwarders being initialized
    def initializeExecutor(self, queue_to_lower: multiprocessing.Queue, queue_from_lower: multiprocessing.Queue,
                           comp_table: NFNComputationList):
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        self.computation_table = comp_table

    def getNext(self, arg: str, amount: int):
        self.checkStreaming(arg)
        self.nameList = arg.splitlines()
        self.nameList.pop(0)
        self.posNameList = 0
        for i in range(0, amount):
            interest = Interest("/repo/r1" + self.nameList[i])
            self.queue_to_lower.put((self.packetID, interest))
            self.posNameList += 1
            #print("Put interest: ", interest, " with packetID: ", self.packetID, " successfully in the queue_to_lower.")
        result = self.queue_from_lower.get()[1].content
        print("Result arrived: ", self.posNameList, result)
        return result

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
