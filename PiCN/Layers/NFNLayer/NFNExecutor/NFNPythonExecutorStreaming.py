"""NFN streaming executor for Named Functions written in Python"""

import multiprocessing

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Packets import Interest, Content, Name


class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self):
        self._language = "PYTHONSTREAM"
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["check_streaming"] = self.check_streaming
        self._sandbox["get_next"] = self.get_next
        self._sandbox["check_end_streaming"] = self.check_end_streaming
        self._sandbox["write_out"] = self.write_out
        self._sandbox["check_get_next_case"] = self.check_get_next_case
        self._sandbox["print"] = print
        self.get_next_buffer: dict = {}
        self.sent_interests: dict = {}
        self.name_list_single: list = None
        self.name_list_multiple: list = None
        self.pos_name_list_single: int = 0
        self.pos_name_list_multiple: int = 0
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
        :param cs: the BaseContentStore to store the Content in write_out
        """
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        self.comp_table = comp_table
        self.cs = cs

    def initialize_get_next_single(self, arg: str):
        """
        check if file is for streaming and if it is fill self.name_list_single with necessary names for single name case
        :param arg: the input with the desired computation names
        """
        # TODO If arg is not for streaming stop here
        if self.check_streaming(arg) is False:
            return "Not for streaming."
        self.name_list_single = arg.splitlines()
        self.name_list_single.pop(0)

    def initialize_get_next_multiple(self, arg: str):
        """
        check if file is for streaming and if it is fill self.name_list_multiple with necessary names for multiple name case
        :param arg: the input with the desired computation names
        """
        if self.name_list_multiple is None:
            self.name_list_multiple = arg.splitlines()
            self.name_list_multiple.pop(0)

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

    def check_get_next_case(self, interest_name: str):
        """
        check which of the get_next cases is needed - if it ends with '/streaming/p*' the single name case is needed
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
        :return the negative amount of digits
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

    def get_next_content(self, arg: str):
        """
        get content from given name for the get next function
        :param arg: the name from which the content is returned
        :return: the content for the name
        """
        next_name = arg
        buffer_output = self.check_buffer(next_name)
        if buffer_output:
            result = buffer_output.content
        else:
            # Interest() gets added to queue_to_lower
            self.queue_to_lower.put((self.packetid, Interest(next_name)))
            self.sent_interests[next_name] = False
            resulting_content_object = self.queue_from_lower.get()[1]
            print("[get_next_content] Resulting content object:", resulting_content_object.name, resulting_content_object.content)
            # Gets stored in buffer if interest doesn't correspond to needed result
            is_content_correct = self.check_for_correct_content(resulting_content_object, next_name)
            while is_content_correct is False:
                buffer_output = self.check_buffer(next_name)
                # If desired interest is in buffer return it and break out of while loop
                if buffer_output:
                    resulting_content_object = buffer_output
                    break
                else:
                    # Get content out of queue_from_lower and check if it is correct -> until correct one is returned
                    resulting_content_object = self.queue_from_lower.get()[1]
                    is_content_correct = self.check_for_correct_content(resulting_content_object, next_name)
            # if correct = result
            result = resulting_content_object.content
            self.sent_interests[resulting_content_object.name.components_to_string()] = True
        return result

    def get_next_single_name(self, arg: str):
        """
        get next for the single name case continues until one /streaming/p.. contains "sdo:endstreaming"
        :param arg: the output from the write_out
        """
        name = arg.split("//")[0]
        if self.check_streaming(name):
            # ASK name built correctly?
            name = name[5:] + "/streaming/p0"
            result = ""
            next_result = self.get_next_content(name)
            while self.check_end_streaming(next_result) is False:
                result += next_result
                name = self.get_following_name(name)
                next_result = self.get_next_content(name)
            return result

    def get_next_multiple_names(self, arg: str):
        """
        get next for the multiple name case
        initalizes name_list_multiple if it isn't already initalized
        :param arg: listing of names "sdo:\n\name1\name2\n...\nameN
        """
        self.initialize_get_next_multiple(arg)
        next_name = self.name_list_multiple[self.pos_name_list_multiple]
        self.pos_name_list_multiple += 1
        return self.get_next_content(next_name)

    def get_next(self, arg: str):
        """
        get next content
        distinguished between both cases and continues for the necessary case
        :param arg: name
        """
        if self.check_get_next_case(arg):
            return self.get_next_single_name(arg)
        else:
            if self.check_streaming(arg):
                return self.get_next_multiple_names(arg)
            # doesn't start with sdo: -> it is a computation
            print("get_next input:", arg)
            first = arg.find("=")
            last = len(arg) - arg[::-1].find("=") - 1
            hash = arg.find("#")
            arg = list(arg)
            arg[first] = '"'
            arg[last] = '"'
            arg[hash] = "_"
            arg = "".join(arg)
            print("get_next after transform:", arg)
            name = Name(arg)
            component_lists = name.components
            first_quot = False
            new_component = ""
            for component in name.components:
                if '"' in str(component):
                    if first_quot is True:
                        new_component += str(component)
                        first_quot = False
                    else:
                        first_quot = True
                if first_quot:
                    new_component += str(component)
            new_component = new_component.replace("b", "/").replace("'", "").replace('"',"")[1:]
            start_of_component = 0
            for i in range (0,len(name.components)):
                if "_(" in str(name.components[i]):
                    start_of_component = i
            comp_list_len = len(name.components)
            for i in range (start_of_component, comp_list_len-2):
                name.components.pop(len(name.components)-2)
            name.components[-2] = new_component.encode("ascii")
            #print("Component list", name.components)
            return self.get_next_content(name)


    def write_out(self, content_content: str):
        """
        stores content object as parts into the content store
        :param contentContent: the content to be written out
        :return: string: computation name + "/streaming/p*"
        """
        print("Computation name: ", self.comp_name)
        content_name = self.comp_name

        content_name += "/streaming/p" + str(self.part_counter)
        content_object = Content(content_name, content_content)
        self.cs.add_content_object(content_object)
        print("[write_out] Last entry in content store:", self.cs.get_container()[-1].content.name,
              self.cs.get_container()[-1].content.content)

        self.part_counter += 1
        write_out_file = "sdo:\n"
        write_out_file += str(self.comp_name)
        write_out_file += "/streaming/p*"
        return write_out_file

    def check_name(self, name: str):
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
            tmp_list = arg.splitlines()
            tmp_list.pop(0)
            for x in tmp_list:
                if self.check_name(x) is False:
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
