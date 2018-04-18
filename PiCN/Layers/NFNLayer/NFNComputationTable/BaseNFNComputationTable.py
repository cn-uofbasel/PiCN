"""Basis for the NFNComputation Tables, including NFNComputationTableEntry and BaseNFNComputationTable and
the Computation Status"""

import abc
import time
from enum import Enum
from typing import List
from PiCN.Packets import Content, Name


class NFNComputationState(Enum):
    START = 0
    FWD = 1
    EXEC = 2

class NFNAwaitListEntry(object):
    """Data Structure storing information about reqests of a running computation
    :param name: name of the request
    """

    def __init__(self, name: Name):
        self.name = name
        self.use_timeout_requests = True if name.components[len(name.components)-1] == b'NFN' else False
        self.time_stamp = time.time()

    def __eq__(self, other):
        if type(other) == NFNAwaitListEntry:
            return self.name == other.name
        elif type(other) == Name:
            return self.name == other

class NFNComputationTableEntry(object):
    """Data Structure storing information about a Running Computation
    :param name: ICN-Name of the computation
    """

    def __init__(self, name: Name):
        self.original_name: Name = name # original name of the computation
        self.awaiting_data: List[NFNAwaitListEntry] = [] # data that are awaited by the computation
        self.available_data: List[Content] = [] # data that are required and now available
        self.comp_state: NFNComputationState = NFNComputationState.START # marker where to continue this computation after requests
        self.time_stamp = time.time() # time at which the computation was started

        self.timeout = 4.0 #timeout before a request expires


    def add_name_to_await_list(self, name):
        """adds a name to the list of awaited data
        :param Name to be added
        """
        self.awaiting_data.append(NFNAwaitListEntry(name))

    def push_data(self, content: Content):
        """check if content was requested, adds entry to available data and removes the name from the await list
        :param content: Content Object that should be added to the computation
        """
        if content.name not in list(map(lambda n: n.name, self.awaiting_data)):
            return
        if content in self.available_data:
            return
        self.available_data.append(content)
        self.awaiting_data.remove(NFNAwaitListEntry(content.name))

    def ready_to_continue(self) -> bool:
        """Returns if all required data were received
        :return True if all data were received, else false
        """
        if len(self.awaiting_data) == 0:
            return True
        else:
            return False

    def ageing(self) -> List[Name]:
        """Age the entries inside the list awaiting data
        :return A list of entries for which timeout reqests must be sent and [] if reqest is fine, None if entry must be deleted
        """
        ts = time.time()
        required_requests = []
        for al_entry in self.awaiting_data:
            if ts > self.timeout + al_entry.time_stamp:
                if not al_entry.use_timeout_requests:
                    return None
                else:
                    required_requests.append(al_entry.name)

        for al_entry in required_requests:
            self.awaiting_data.remove(al_entry)
            al_entry.time_stamp = time.time()
            self.awaiting_data.append(al_entry)
        return  required_requests

    def __eq__(self, other):
        return self.original_name == other.original_name


class BaseNFNComputationTable(object):

    def __init__(self):
        self.container: List[BaseNFNComputationTable] = []

    @abc.abstractmethod
    def add_computation(self, name):
        """add a computation to the Computation table (i.e. start a new computation)
        :param name: icn-name of the computation
        """

    @abc.abstractmethod
    def is_comp_running(self, name) -> bool:
        """checks if a name was already added to the list of running computations
        :param name: name to check
        :return True if computation was already added, else false
        """

    @abc.abstractmethod
    def push_data(self, content):
        """add received data to running computations
        :param content: content to be added
        """

    @abc.abstractmethod
    def get_ready_computations(self) -> List[NFNComputationTableEntry]:
        """get all computations that are ready to continue
        :return List of all NFNComputationTableEntrys which are ready
        """

    @abc.abstractmethod
    def ageing(self) -> List[Name]:
        """age the running computations.
        Removes entries which timed out and tells for which entries a timeout request must be sent
        :return List of Names for which Timeout Reqest must be sent.
        """
