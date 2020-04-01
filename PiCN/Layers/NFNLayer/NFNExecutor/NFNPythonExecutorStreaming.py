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
        self._sandbox["check_streaming"] = self.check_streaming
        self._sandbox["getNext"] = self.getNext
        self._sandbox["check_end_streaming"] = self.check_end_streaming
        self._sandbox["writeOut"] = self.writeOut
        self._sandbox["checkGetNextCase"] = self.checkGetNextCase
        self._sandbox["print"] = print
        self.get_next_buffer: dict = {}
        self.sent_interests: dict = {}
        self.name_list: list = None
        self.pos_name_list: int = 0
        self.queue_to_lower: multiprocessing.Queue = None
        self.queue_from_lower: multiprocessing.Queue = None
        self.comp_table: NFNComputationList = None
        self.cs: BaseContentStore = None
        self.packetid: int = None
        self.comp_name: str = None
        self.part_counter: int = 0

    def initialize_executor(self, queue_to_lower: multiprocessing.Queue, queue_from_lower: multiprocessing.Queue,
                           comp_table: NFNComputationList, cs: BaseContentStore):
        """
        setter function to set both queues, the computation table and the content store after the forwarders being initialized
        :param queue_to_lower: queue to lower layer
        :param queue_from_lower: queue from lower layer
        :param comp_table: the NFNComputationList
        :param cs: the BaseContentStore to store the Content in writeOut
        """
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        self.comp_table = comp_table
        self.cs = cs

    def initialize_get_next(self, arg: str):
        """
        check if file is for streaming and if it is fills self.name_list with necessary names
        :param arg: the input with the desired computation names
        """
        if self.name_list is None:
            # TODO If arg is not for streaming stop here
            if self.check_streaming(arg) is False:
                return "Not for streaming."
            self.name_list = arg.splitlines()
            self.name_list.pop(0)

    def check_buffer(self, interest_name: str):
        """
        check if interest is in the buffer and returns the content object if it is present
        :param interest: the interest name
        """
        if interest_name in self.get_next_buffer:
            return self.get_next_buffer[interest_name]
        else:
            return False

    def check_for_correct_content(self, content_object: Content, content_name: str):
        """
        check if the content from content_object corresponds to the interest requested with content_name
        if true returns true
        else returns false and stores content_object in get_next_buffer if it is for this computation
        if not relevant for this computation it is put to self.queue_from_lower again
        :param content_object: the content_object to compare
        :param next_name: the corresponding name
        :return:
        """
        content_object_name_as_string = content_object.name.components_to_string()
        if content_name == content_object_name_as_string:
            return True
        else:
            # Content is not from requested interest
            # if content is from this computation store in buffer put in self.queue_from_lower
            if content_object_name_as_string in self.sent_interests:
                self.get_next_buffer[content_object_name_as_string] = content_object
            else:
                # TODO test this case - content_object not from this computation
                self.queue_from_lower.put(content_object)
            return False

    def checkGetNextCase(self, interest_name: str):
        """
        check which of the getNext cases is needed - if it ends with '/streaming/p*' the single name case is needed
        :param interest_name: the interest name
        """
        if interest_name.endswith("/streaming/p*"):
            return True
        else:
            return False

    def get_amount_of_digits(self, name: str):
        """
        get the amount of digits on the part of the single name case
        :param name: the name from which the amount of digit has to be returned
        :return minus the amount of digits
        """
        x = -1
        while name[x - 1].isdigit():
            x -= 1
        if name[:x].endswith("/streaming/p"):
            return x

    def get_following_name(self, name: str):
        """
        get the following name with help of the negative amount of digits (get_amount_of_digits)
        :param name: the name from which the following has to be found
        :return: the following name
        """
        amount_of_digits = self.get_amount_of_digits(name)
        number = int(name[amount_of_digits:])
        number += 1
        following_name = name[:amount_of_digits]
        following_name += str(number)
        return following_name

    def getNextContent(self, arg: str, multiple: bool = False):
        next_name = arg
        bufferOutput = self.check_buffer(next_name)
        if bufferOutput:
            result = bufferOutput.content
        else:
            # Interest() gets added to queue_to_lower
            self.queue_to_lower.put((self.packetid, Interest(next_name)))
            self.sent_interests[next_name] = False
            resultingContentObject = self.queue_from_lower.get()[1]
            print("[getNextContent] Resulting content object:", resultingContentObject.name, resultingContentObject.content)
            # Gets stored in buffer if interest doesn't correspond to needed result
            isContentCorrect = self.check_for_correct_content(resultingContentObject, next_name)
            while isContentCorrect is False:
                bufferOutput = self.check_buffer(next_name)
                # If desired interest is in buffer return it and break out of while loop
                if bufferOutput:
                    resultingContentObject = bufferOutput
                    break
                else:
                    # Get content out of queue_from_lower and check if it is correct -> until correct one is returned
                    resultingContentObject = self.queue_from_lower.get()[1]
                    isContentCorrect = self.check_for_correct_content(resultingContentObject, next_name)
            # if correct = result
            result = resultingContentObject.content
            self.sent_interests[resultingContentObject.name.components_to_string()] = True
            if multiple:
                self.pos_name_list += 1
        return result

    def getNextSingleName(self, arg: str):
        self.initialize_get_next(arg)
        name = self.name_list[0]
        name = name[:len(name)-1] + str(0)
        nextResult = self.getNextContent(name)
        result = ""
        while self.check_end_streaming(nextResult) is False:
            result += nextResult
            name = self.get_following_name(name)
            nextResult = self.getNextContent(name)
        return result

    def getNextMultipleNames(self, arg: str):
        self.initialize_get_next(arg)
        next_name = self.name_list[self.pos_name_list]
        return self.getNextContent(next_name, True)

    def getNext(self, arg: str):
        arg = "sdo:\n/repo/r1/test/streaming/p*"
        if self.checkGetNextCase(arg):
            return self.getNextSingleName(arg)
        else:
            return self.getNextMultipleNames(arg)

    def writeOut(self, contentContent: str):
        # ASK writeOut doesn't check endOfStreaming?
        print("Computation name: ", self.comp_name)
        contentName = self.comp_name

        contentName += "/streaming/p" + str(self.part_counter)
        content_object = Content(contentName, contentContent)
        self.cs.add_content_object(content_object)
        print("[writeOut] Last entry in content store:", self.cs.get_container()[-1].content.name,
              self.cs.get_container()[-1].content.content)

        self.part_counter += 1
        writeOutFile = "sdo:\n"
        writeOutFile += str(self.comp_name)
        writeOutFile += "/streaming/p*"
        # ASK if this output is correct with the comp_name
        return writeOutFile

    def checkForName(self, name: str):
        """
        check if name starts with '/'
        :param name: name to check
        """
        if name[0] == "/":
            return True
        else:
            return False

    def check_streaming(self, arg: str):
        """check if file is form streaming and lines start with a '/'
        :param arg: file to check
        """
        # Check if String is empty
        if not arg:
            return False
        # Check if streaming prefix is available
        elif arg.startswith("sdo:"):
            print("[check_streaming] File is for streaming")
            tmpList = arg.splitlines()
            tmpList.pop(0)
            for x in tmpList:
                if self.checkForName(x) is False:
                    return False
            return True
        # Wrong prefix, file is not for streaming
        else:
            return False

    def check_end_streaming(self, arg: str):
        """
        check if its the end of the stream¨
        :param arg: content to check
        """
        return arg.endswith("sdo:endstreaming")
