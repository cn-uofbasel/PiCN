"""NFN streaming executor for Named Functions written in Python"""

import multiprocessing

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Packets import Interest, Content


class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self):
        self._language = "PYTHONSTREAM"
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["checkStreaming"] = self.checkStreaming
        self._sandbox["getNext"] = self.getNext
        self._sandbox["checkEndStreaming"] = self.checkEndStreaming
        self._sandbox["writeOut"] = self.writeOut
        self._sandbox["checkGetNextCase"] = self.checkGetNextCase
        self._sandbox["print"] = print
        self.getNextBuffer: dict = {}
        self.sentInterests: dict = {}
        self.nameList: list = None
        self.posNameList: int = 0
        self.queue_to_lower: multiprocessing.Queue = None
        self.queue_from_lower: multiprocessing.Queue = None
        self.computation_table: NFNComputationList = None
        self.cs: BaseContentStore = None
        self.packetID : int = None
        self.partCounter : int = 0
        self.writeOutFile: str = "sdo:" # writeOutFile as local variable to store single writeOut name


    # Setter function to set both queues after the forwarders being initialized
    def initializeExecutor(self, queue_to_lower: multiprocessing.Queue, queue_from_lower: multiprocessing.Queue,
                           comp_table: NFNComputationList, cs: BaseContentStore):
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        self.computation_table = comp_table
        self.cs = cs


    # Checks if file is for streaming and if so fills self.nameList
    def initializeGetNext(self, arg: str):
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
                # TODO test this case - contentObject not from this computation
                self.queue_from_lower.put(contentObject)
            return False


    # Check if arg ends with /streaming/p*
    def checkGetNextCase(self, arg: str):
        if arg[-1].isdigit():
            x = -1
            while arg[x-1].isdigit():
                x -= 1
            if arg[:x].endswith("/streaming/p"):
                return True
            # arg ended with digits but not with /streaming/p*
            else:
                return False
        else:
            return False


    def getAmountOfDigits(self, arg: str):
        x = -1
        while arg[x-1].isdigit():
            x -= 1
        if arg[:x].endswith("/streaming/p"):
            return x


    def getFollowingName(self, arg: str):
        amountOfDigits = self.getAmountOfDigits(arg)
        number = int(arg[amountOfDigits:])
        number += 1
        followingName = arg[:amountOfDigits]
        followingName += str(number)
        return followingName


    def getNextContent(self, arg: str, multiple: bool = False):
        nextName = arg
        bufferOutput = self.checkBuffer(nextName)
        if bufferOutput:
            result = bufferOutput.content
        else:
            # Interest() gets added to queue_to_lower
            self.queue_to_lower.put((self.packetID, Interest(nextName)))
            self.sentInterests[nextName] = False
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
            self.sentInterests[resultingContentObject.name.components_to_string()] = True
            if multiple:
                self.posNameList += 1
        return result


    def getNextSingleName(self, arg: str):
        nextResult = self.getNextContent(arg)
        result = nextResult
        name = arg
        while self.checkEndStreaming(nextResult) is False:
            result += nextResult
            nextResult = self.getNextContent(name)
            name = self.getFollowingName(name)
        return result


    def getNextMultipleNames(self, arg: str):
        self.initializeGetNext(arg)
        nextName = self.nameList[self.posNameList]
        return self.getNextContent(nextName)


    # WIP getNext has to work with /streaming/p*
    # ASK: amount not used
    def getNext(self, arg: str, amount: int):
        if self.checkGetNextCase(arg):
            return self.getNextSingleName(arg)
        else:
            return self.getNextMultipleNames(arg)


    def writeOut(self, contentContent: str):
        self.writeOutFile += "\n"
        if self.checkEndStreaming(contentContent):
            self.writeOutFile += "sdo:endstreaming"
            return "Stream ended."

        # WIP ASK get computation name out of execution environment - which version of dict? -> how to handle content which weren't received from getNext?
        contentName = (list(self.sentInterests.keys())[-1])
        while self.sentInterests[contentName] is False:
            contentName = (list(self.sentInterests.keys())[-1])

        # DONE after being used content can be removed from self.sentInterests
        del self.sentInterests[contentName]

        contentName += "/streaming/p" + str(self.partCounter)
        contentObject = Content(contentName, contentContent)
        self.cs.add_content_object(contentObject)
        print("Last entry in content store: ", self.cs.get_container()[-1].content.name, self.cs.get_container()[-1].content.content)
        self.writeOutFile += contentName
        self.partCounter += 1
        return self.writeOutFile


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

    def checkEndStreaming(self, arg: str):
        return arg.endswith("sdo:endstreaming")