"""NFN streaming executor for Named Functions written in Python"""

import multiprocessing
import time

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Packets import Interest, Content, Name, Nack


class NFNPythonExecutorStreaming(NFNPythonExecutor):

    def __init__(self):
        self._language = "PYTHONSTREAM"
        self._sandbox = NFNPythonExecutor()._init_sandbox()
        self._sandbox["check_end_streaming"] = self.check_end_streaming
        self._sandbox["get_next"] = self.get_next
        self._sandbox["write_out"] = self.write_out
        self._sandbox["last_write_out"] = self.last_write_out
        self._sandbox["write_out_on_get_next"] = self.write_out_on_get_next
        self._sandbox["print"] = print
        self._sandbox["sleep"] = time.sleep
        self.get_next_buffer: dict = {}
        self.sent_interests: dict = {}
        self.name_list_single: list = None
        self.name_list_multiple: list = None
        self.pos_name_list_multiple: int = 0
        self.queue_to_lower: multiprocessing.Queue = None
        self.queue_from_lower: multiprocessing.Queue = None
        self.cs: BaseContentStore = None
        self.packetid: int = None
        self.comp_name: str = None
        self.get_next_part_counter: int = 0
        self.write_out_part_counter: int = -1
        self.classic: bool = False


    def initialize_executor(self, queue_to_lower: multiprocessing.Queue, queue_from_lower: multiprocessing.Queue, cs: BaseContentStore, classic: bool = False):
        """
        Setter function to set both queues, the computation table, the content store and the pending interest table
        after the forwarders have been initialized.
        :param queue_to_lower: queue to lower layer
        :param queue_from_lower: queue from lower layer
        :param cs: the BaseContentStore to store the content during the write_out
        :param classic: a flag which changes streaming to the classical way - doesn't request new object before
                        returning the result
        """
        self.queue_to_lower = queue_to_lower
        self.queue_from_lower = queue_from_lower
        self.cs = cs
        self.classic = classic


    def initialize_get_next_single(self, arg: str):
        """
        Checks if the file is for streaming and if it is, self.name_list_single gets filled with the necessary names
        for the single name case.
        :param arg: the input with the desired computation names
        """
        if self.check_streaming(arg) is False:
            return "Not for streaming."
        self.name_list_single = arg.splitlines()
        self.name_list_single.pop(0)


    def initialize_get_next_multiple(self, arg: str):
        """
        Check if the file is for streaming and if it is, self.name_list_multiple gets filled with the necessary names
        for the multiple name case.
        :param arg: the input with the desired computation names
        """
        if self.name_list_multiple is None:
            self.name_list_multiple = arg.splitlines()
            self.name_list_multiple.pop(0)
            self.pos_name_list_multiple = 0


    def check_name(self, name: str):
        """
        Checks if name either starts with '/' or it is the last component of a stream.
        :param name: name to check
        :return: True if it is. False if not.
        """
        if name[0] == "/" or self.check_end_streaming(name):
            return True
        else:
            return False


    def check_streaming(self, arg: str):
        """
        Checks if the file is in the streaming format.
        The file starts with 'sdo:' and every line starts with a '/'
        :param arg: file to check
        :return: True if it is in the correct format. False if not.
        """
        if not arg:
            return False
        elif arg.startswith("sdo:"):
            print("[check_streaming] File is for streaming")
            tmp_list = arg.splitlines()
            tmp_list.pop(0)
            for x in tmp_list:
                if self.check_name(x) is False:
                    return False
            return True
        else:
            return False


    def check_end_streaming(self, arg: str):
        """
        Check if it the content ends with "sdo:endstreaming".
        :param arg: content to check
        :return: True if it is the end. False if not.
        """
        return arg.endswith("sdo:endstreaming")


    def check_buffer(self, interest_name: str):
        """
        Checks if interest is in the buffer and returns the content object if it is.
        :param interest: the interest name
        :return: The content object if it is in the buffer. False if it is not in the buffer.
        """
        if str(interest_name) in self.get_next_buffer:
            return self.get_next_buffer[str(interest_name)]
        else:
            return False


    def check_for_correct_content(self, content_object: Content, content_name: str):
        """
        Checks if the content from content_object corresponds to the interest requested with content_name.
        If the content is not relevant for this computation it is put to self.queue_from_lower again.
        :param content_object: the content_object to compare
        :param next_name: the corresponding name
        :return: True if it is the correct content. If the content doesn't correspond to the name the content object
        is stored in the buffer and False is returned.
        """
        if isinstance(content_name, Name):
            content_name = content_name.to_string() # inner comp is a name instead of a string
            # outter comp starts with sdo:\n
        elif content_name.startswith("sdo:\n"):
            content_name = content_name[5:]

        content_object_name_as_string = content_object.name.components_to_string()
        if content_name == content_object_name_as_string:
            return True
        else:
            # Content is not from requested interest
            # if content is from this computation, store in buffer else put in self.queue_from_lower
            if content_object_name_as_string in self.sent_interests:
                self.get_next_buffer[content_object_name_as_string] = content_object
            else:
                self.queue_from_lower.put(content_object)
            return False


    def check_for_metatitle(self, interest_name: str):
        """
        Checks if a metatitle is present (ends with '/streaming/p*').
        :param interest_name: the interest name
        :return: True if it is a metatitle. False if not.
        """
        if interest_name.endswith("/streaming/p*"):
            return True
        else:
            return False


    def check_for_singlename(self, interest_name: str):
        while interest_name[-1].isdigit():
            interest_name = interest_name[:-1]
        if interest_name.endswith("/streaming/p"):
            return True
        else:
            return False


    def get_amount_of_digits(self, name: str):
        """
        Gets the negative amount of digits after the '/streaming/p' on the single name.
        :param name: the name from which the amount of digit has to be returned
        :return the negative amount of digits
        """
        x = -1
        while name[x - 1].isdigit():
            x -= 1
        if name[:x].endswith("/streaming/p"):
            return x


    def get_following_name(self, name: Name):
        """
        Gets the name for the next part with help of the negative amount of digits (get_amount_of_digits).
        :param name: the name from which the following has to be found
        :return: the following name
        """
        name = str(name)
        amount_of_digits = self.get_amount_of_digits(name)
        number = int(name[amount_of_digits:])
        number += 1
        following_name = name[:amount_of_digits]
        following_name += str(number)
        return following_name


    def get_content_from_queue_from_lower(self):
        """
        Gets content from the queue from lower and checks if the result is a list with the packetid on the first entry
        and the content object on the second entry
        :return: the next content object from the queue_from_lower
        """
        queue_from_lower_entry = self.queue_from_lower.get()
        if isinstance(queue_from_lower_entry, list):
            if isinstance(queue_from_lower_entry[1], Nack):
                print("NACK:", queue_from_lower_entry[1].interest, queue_from_lower_entry[1].reason)
            return queue_from_lower_entry[1]
        else:
            if isinstance(queue_from_lower_entry, Nack):
                print("NACK:", queue_from_lower_entry.interest, queue_from_lower_entry.reason)
            return queue_from_lower_entry



    def stream_part(self, result: str, resulting_content_object: Content):
        """
        Checks if the result is meta and retrieves the following part if it is.
        :param result: The result as content
        :param resulting_content_object: the result as a content object
        :return: the content object which was given as a parameter or the result of the following part if result is
                 a metatitle
        """
        if self.check_for_metatitle(result):
            if str(resulting_content_object.name) not in self.get_next_buffer:
                self.get_next_buffer[str(resulting_content_object.name)] = resulting_content_object
            print("[Streaming] Part", self.get_next_part_counter, "starts here.")
            next_name = str(resulting_content_object.name) + "//streaming/p" + str(self.get_next_part_counter)
            if self.classic is False:
                result = self.get_next_single_name(next_name)
            else:
                result = self.get_next_single_name_classic(next_name)
            print("[Streaming] Part", self.get_next_part_counter, "ends here with result:", result)
            self.get_next_part_counter += 1
            if self.check_end_streaming(result):
                return None
        return result


    def get_content(self, next_name: str):
        """
        Handles getting the content. Checks if the name is present in the buffer otherwise gets it from the
        queue_from_lower. If result is a metatitle, the following part is retrieved.
        :param arg: the name from which the content is returned
        :return: the content for the name
        """
        buffer_output = self.check_buffer(next_name)
        if buffer_output:
            print("[get_next_content] Resulting content object out of the buffer:", buffer_output.name, buffer_output.content)
            resulting_content_object = buffer_output
            result = buffer_output.content
        else:
            resulting_content_object = self.get_content_from_queue_from_lower()
            if isinstance(resulting_content_object, Interest):
                print("[get_next_content] Resulting object is interest:", resulting_content_object.name, ", instead of content object with name:", next_name)
            else:
                print("[get_next_content] Resulting content object(desired name, resulting name):", next_name, resulting_content_object.name)
            # Gets stored in buffer if interest doesn't correspond to needed result
            is_content_correct = self.check_for_correct_content(resulting_content_object, next_name)
            while is_content_correct is False:
                #print("[get_next_content] Content wasn't correct", resulting_content_object.name)
                buffer_output = self.check_buffer(next_name)
                # If desired interest is in buffer return it and break out of while loop
                if buffer_output:
                    resulting_content_object = buffer_output
                    break
                else:
                    # Get content out of queue_from_lower and check if it is correct -> until correct one is returned
                    #print("[get_next_content] Content wasn't correct and not avaiable in the buffer.")
                    resulting_content_object = self.get_content_from_queue_from_lower()
                    #print("[get_next_content] Resulting content object:", resulting_content_object.name, next_name)
                    is_content_correct = self.check_for_correct_content(resulting_content_object, next_name)

            result = resulting_content_object.content
        result = self.stream_part(result, resulting_content_object)
        return result


    def get_next_single_name(self, arg: str):
        """
        get next for the single name case. Before returning the result the next name get already put into the
        queue_to_lower. The first name is the only one which is put into the queue immediately before requesting.
        :param arg: the output from the write_out
        """
        current_name = arg
        if self.get_next_part_counter == 0:
            self.sent_interests[str(current_name)] = True
            self.queue_to_lower.put((self.packetid, Interest(current_name)))
        result = self.get_content(current_name)
        if self.check_end_streaming(result) is False:
            next_name = self.get_following_name(current_name)
            self.sent_interests[str(next_name)] = True
            self.queue_to_lower.put((self.packetid, Interest(next_name)))
        return result


    def get_next_multiple_names(self, arg: str):
        """
        get next for the multiple name case. Before returning the result the next name get already put into the
        queue_to_lower. The first name is the only one which is put into the queue immediately before requesting.
        :param arg: list of the names "sdo:\n\name1\name2\n...\nameN
        """
        self.initialize_get_next_multiple(arg)
        if self.pos_name_list_multiple < len(self.name_list_multiple)-1:
            current_name = self.name_list_multiple[self.pos_name_list_multiple]
            # Only first call puts two names (current_name and next_name) in the queue_to_lower. Next call only puts next_name
            if self.pos_name_list_multiple == 0:
                self.sent_interests[str(current_name)] = True
                self.queue_to_lower.put((self.packetid, Interest(current_name)))
            self.pos_name_list_multiple += 1
            next_name = self.name_list_multiple[self.pos_name_list_multiple]
            if self.check_end_streaming(next_name) is False:
                self.sent_interests[str(next_name)] = True
                self.queue_to_lower.put((self.packetid, Interest(next_name)))
            result = self.get_content(current_name)
            return result
        elif self.pos_name_list_multiple == len(self.name_list_multiple)-1:
            self.name_list_multiple = None
        else:
            return None


    def get_next_single_name_classic(self, arg: str):
        """
        get_next for the classic single name case. The name only gets put in the queue_to_lower before requesting it.
        :param arg: the output from the write_out
        """
        current_name = arg
        self.sent_interests[str(current_name)] = True
        self.queue_to_lower.put((self.packetid, Interest(current_name)))
        result = self.get_content(current_name)
        return result


    def get_next_multiple_names_classic(self, arg: str):
        """
        get_next for the classic multiple name case. The name only gets put in the queue_to_lower before requesting it.
        :param arg: list of the names "sdo:\n\name1\name2\n...\nameN
        """
        self.initialize_get_next_multiple(arg)
        if self.pos_name_list_multiple < len(self.name_list_multiple)-1:
            current_name = self.name_list_multiple[self.pos_name_list_multiple]
            self.sent_interests[str(current_name)] = True
            self.queue_to_lower.put((self.packetid, Interest(current_name)))
            self.pos_name_list_multiple += 1
            result = self.get_content(current_name)
            return result
        elif self.pos_name_list_multiple == len(self.name_list_multiple)-1:
            self.name_list_multiple = None


    def transform_inner(self, arg: str):
        """
        Transform the inner name to correct syntax so it can be parsed. Replaces first and last '=' with an '"' and the
        '#' with an '_'.
        :param arg: The name as a string to be transformed
        :return: the transformed string
        """
        first = arg.find("=")
        last = len(arg) - arg[::-1].find("=") - 1
        hash = arg.find("#")
        arg = list(arg)
        arg[first] = '"'
        arg[last] = '"'
        arg[hash] = "_"
        arg = "".join(arg)
        return arg


    def encode_name_components(self, name: Name):
        """
        Encodes the name components so it can be handled from the lower layers.
        :param name: the name to be encoded
        :return: the encoded name
        """
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
        new_component = new_component.replace("'b'", "/").replace("b'", "")[:-1]
        if "=" not in new_component and '"' in new_component:
            new_component = new_component.replace('"', "")
        start_of_component = 0
        for i in range(0, len(name.components)):
            if "_(" in str(name.components[i]):
                start_of_component = i
        comp_list_len = len(name.components)
        for i in range(start_of_component, comp_list_len - 2):
            name.components.pop(len(name.components) - 2)
        name.components[-2] = new_component.encode("ascii")
        return name


    def get_next_inner_computation(self, arg: str):
        """
        Handles the inner computation part from get_next. Transforms and encodes the name and puts it into the
        queue_to_lower and calls get_content() to retrieve the result.
        :param arg: the name as a string
        :return: the content from the content object
        """
        print("[get_next - inner computation] starts here.")
        # Start of transformation and component encoding
        name_str = self.transform_inner(arg)
        # print("[get_next - inner computation] after transform:", arg)
        name_after_transform = Name(name_str)
        name = self.encode_name_components(name_after_transform)
        # End of transformation and component encoding
        print("[get_next - inner computation] after encoding:", name)
        self.queue_to_lower.put((self.packetid, Interest(name)))
        inner_result = self.get_content(name)
        print("[get_next - inner computation] ends here with result:", inner_result)
        return inner_result


    def get_next(self, arg: str):
        """
        The get_next function which is used for the named functions.
        This function handles getting the desired content according to its case. Two cases are possible.
        The multi name case for getting the next part if the length of the stream is given.
        The handling of an inner computation where the name has to be changed to thr correct format before getting the
        content.
        :param arg: the name as a string
        :return: the content from the content object
        """
        if self.check_for_singlename(arg):
            if self.classic is False:
                return self.get_next_single_name(arg)
            else:
                return self.get_next_single_name_classic(arg)
        if self.check_streaming(arg):
            if self.classic is False:
                return self.get_next_multiple_names(arg)
            else:
                return self.get_next_multiple_names_classic(arg)
        else:
            return self.get_next_inner_computation(arg)


    def write_out(self, content_content: str):
        """
        The write_out function which is used for the named functions.
        Stores content object as parts into the content store. Before the first element is stored a meta title is stored
        into the content store so the node who gets this content object can detect and start the stream.
        :param contentContent: the content object to be stored out
        """
        print("[write_out] Computation name: ", self.comp_name)
        # meta_title_content object creation to return as a first part
        if self.write_out_part_counter < 0:
            metatitle_content = Content(self.comp_name, "sdo:\n" + str(self.comp_name) + "/streaming/p*")
            self.queue_to_lower.put((self.packetid, metatitle_content))
            # self.cs.add_content_object(metatitle_content) TODO not needed? 

        # actual content_object for streaming
        self.write_out_part_counter += 1
        content_name = self.comp_name
        content_name += "/streaming/p" + str(self.write_out_part_counter)
        content_object = Content(content_name, content_content)
        self.cs.add_content_object(content_object)
        print("[write_out] Last entry in content store:", self.cs.get_container()[-1].content.name,
              self.cs.get_container()[-1].content.content)


    def last_write_out(self):
        """
        The last_write_out function which is used for the named functions.
        Stores the last content object with content = "sdo:endstreaming" into the content store. This is used after the last part is added into the content store to detect the end of the stream.
        """
        end_name = self.comp_name
        self.write_out_part_counter += 1
        end_name += "/streaming/p" + str(self.write_out_part_counter)
        end_streaming_content_object = Content(end_name, "sdo:endstreaming")
        self.cs.add_content_object(end_streaming_content_object)
        print("[last_write_out] Last entry in content store:", self.cs.get_container()[-1].content.name,
              self.cs.get_container()[-1].content.content)

    def write_out_on_get_next(self, arg: Name):
        """
        Streaming function for inner nodes. Runs get_next and writes out the result until end of stream is reached.
        :param arg: The name of the computation to stream the parts.
        """
        res = self.get_next(arg)
        while res and self.check_end_streaming(res) is False:
            self.write_out(res)
            res = self.get_next(arg)
        self.last_write_out()