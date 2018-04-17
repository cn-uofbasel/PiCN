"""Basis for the NFNComputation Tables, including NFNComputationTableEntry and BaseNFNComputationTable and
the Computation Status"""

import abc
from enum import Enum
from typing import List
from PiCN.Packets import Content, Name


class NFNComputationState(Enum):
    START = 0
    FWD = 1
    EXEC = 2

class NFNComputationTableEntry(object):
    """Data Structure storing information about a Running Computation
    :param name: ICN-Name of the computation
    """

    def __init__(self, name: Name):
        self.original_name: Name = name # original name of the computation
        self.awaiting_data: List[Name] = [] # data that are awaited by the computation
        self.available_data: List[Content] = [] # data that are required and now available
        self.comp_state: NFNComputationState = NFNComputationState.START # marker where to continue this computation after requests

    def push_data(self, content: Content):
        """check if content was requested, adds entry to available data and removes the name from the await list
        :param content: Content Object that should be added to the computation
        """
        if content.name not in self.awaiting_data:
            return
        if content in self.available_data:
            return
        self.available_data.append(content)
        self.awaiting_data.remove(content.name)

    def ready_to_continue(self) -> bool:
        """Returns if all required data were received
        :return True if all data were received, else false
        """
        if len(self.awaiting_data) == 0:
            return True
        else:
            return False

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
