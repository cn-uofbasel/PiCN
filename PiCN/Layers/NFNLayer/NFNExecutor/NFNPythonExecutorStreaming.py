"""NFN streaming executor for Named Functions written in Python"""

import multiprocessing

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Packets import Interest, Content


class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self):  # , queue_to_lower, queue_from_lower):
        self._language = "PYTHONSTREAM"
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["checkStreaming"] = self.checkStreaming
        self._sandbox["getNext"] = self.getNext
        self._sandbox["writeOut"] = self.writeOut
        self._sandbox["print"] = print
        self.getNextBuffer: dict = {}
        self.sentInterests: list = []
        self.nameList: list = None
        self.posNameList: int = 0
        self.queue_to_lower: multiprocessing.Queue = None
        self.queue_from_lower: multiprocessing.Queue = None
        self.computation_table: NFNComputationList = None
        self.cs: BaseContentStore = None
        self.packetID : int = None

    # Setter function to set both queues after the forwarders being initialized
    def initializeExecutor(self, queue_to_lower: multiprocessing.Queue, queue_from_lower: multiprocessing.Queue,
                           comp_table: NFNComputationList, cs: BaseContentStore):
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        self.computation_table = comp_table
        self.cs = cs

    # Checks if file is for streaming and if so fills self.nameList
    def initializeGetNext(self, arg: str, amount: int):
        if self.nameList is None:
            self.checkStreaming(arg)
            self.nameList = arg.splitlines()
            self.nameList.pop(0)

    # Checks if name is in the buffer and returns the content object if it is
    # else returns false
    def checkBuffer(self, interest: str):
         if interest in self.getNextBuffer:
             return self.getNextBuffer[interest]
         else:
             return False

    # Checks if the content from contentObject corresponds to the interest requested with nextName
    # if true returns true
    # else returns false and stores contentObject in getNextBuffer if it is for this computation
    # if it is no relevant for this computation it is put to the self.queue_from_lower again
    def checkForCorrectContent(self, contentObject: Content, nextName: str):
        contentObjectNameAsString = contentObject.name.components_to_string()
        if nextName == contentObjectNameAsString:
            return True
        else:
            # Content is not from requested interest
            # if content is from this computation store in buffer put in self.queue_from_lower
            if contentObjectNameAsString in self.sentInterests:
                self.getNextBuffer[contentObjectNameAsString] = contentObject
            else:
                self.queue_from_lower.put(contentObject) # TODO: test this
            return False

    def getNext(self, arg: str, amount: int):
        self.initializeGetNext(arg, amount)
        nextName = self.nameList[self.posNameList]
        # Check if interest is in getNextBuffer
        bufferOutput = self.checkBuffer(nextName)
        if bufferOutput:
            result = bufferOutput.content
        else:
            # Interest() gets added to queue_to_lower
            self.queue_to_lower.put((self.packetID, Interest(nextName)))
            self.sentInterests.append(nextName)
            resultingContentObject = self.queue_from_lower.get()[1]
            # Gets stored in buffer if interest doesn't correspond to needed result
            isContentCorrect = self.checkForCorrectContent(resultingContentObject, nextName)

            while isContentCorrect is False:
                bufferOutput = self.checkBuffer(nextName)
                # If desired interest is in buffer return it and break out of while loop
                if bufferOutput:
                    resultingContentObject = bufferOutput
                    break
                else:
                    # Get content out of queue_from_lower and check if it is correct -> until correct one is returned
                    resultingContentObject = self.queue_from_lower.get()[1]
                    isContentCorrect = self.checkForCorrectContent(resultingContentObject, nextName)

            # if correct = result
            result = resultingContentObject.content
            self.posNameList += 1

        return result

    def writeOut(self):
        return "In progress..."

    # Helper function to check if the string starts with '/'
    def checkForName(self, name: str):
        if name[0] == "/":
            return True
        else:
            return False

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