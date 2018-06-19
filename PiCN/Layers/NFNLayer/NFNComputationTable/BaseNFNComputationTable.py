"""Basis for the NFNComputation Tables, including NFNComputationTableEntry and BaseNFNComputationTable and
the Computation Status"""

import abc
import time
from enum import Enum
from typing import List, Dict
from PiCN.Packets import Content, Name, Interest

from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.R2C import BaseR2CHandler, TimeoutR2CHandler
from PiCN.Layers.NFNLayer.Parser import AST

class NFNComputationState(Enum):
    START = 0
    FWD = 1
    EXEC = 2
    REWRITE = 3
    WRITEBACK=4

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
    :param id: ID given from layer communication
    :param interest: the original Interest message
    :param ast: name parsed and transformed to Abstract Syntax Tree
    :param r2cclient: r2cclient handler that selects and handles messages to be handled
    """

    def __init__(self, name: Name, id: int=0, interest: Interest=None, ast: AST=None, r2cclient: BaseR2CHandler=None,
                 parser: DefaultNFNParser=DefaultNFNParser()):
        self.original_name: Name = name # original name of the computation
        self.id = id
        self.interest = interest
        self.ast: AST = ast
        self.r2cclient: BaseR2CHandler = r2cclient if r2cclient is not None else TimeoutR2CHandler() # r2c clients used for ageing
        self.awaiting_data: List[NFNAwaitListEntry] = [] # data that are awaited by the computation
        self.available_data: Dict[Name, Content] = {} # data that are required and now available
        self.rewrite_list: List[Name] = [] # list of all possible rewrites
        self.parser = parser
        self.comp_state: NFNComputationState = NFNComputationState.START # marker where to continue this computation after requests
        self.time_stamp = time.time() # time at which the computation was started
        self.timeout = 4.0 #timeout before a request expires

    def add_name_to_await_list(self, name):
        """adds a name to the list of awaited data
        :param Name to be added
        """
        self.awaiting_data.append(NFNAwaitListEntry(name))

    def push_data(self, content: Content) -> bool:
        """check if content was requested, adds entry to available data and removes the name from the await list
        :param content: Content Object that should be added to the computation
        :return True if content was required, else False
        """
        if self.comp_state == NFNComputationState.REWRITE:
            if type(self.rewrite_list[0]) == Name:
                rw_name = self.rewrite_list[0]
            else:
                rw_name = self.parser.nfn_str_to_network_name(self.rewrite_list[0])
            if rw_name == content.name:
                self.comp_state = NFNComputationState.WRITEBACK
                self.available_data[content.name] = content.content
                return True
        if content.name not in list(map(lambda n: n.name, self.awaiting_data)):
            return False
        if content.name in self.available_data:
            return False
        self.available_data[content.name] = content.content
        self.awaiting_data.remove(NFNAwaitListEntry(content.name))
        return True

    def ready_to_continue(self) -> bool:
        """Returns if all required data were received, excludes R2C
        :return True if all data were received, else false
        """
        if self.comp_state == NFNComputationState.WRITEBACK:
            return True
        l = list(filter(lambda n: b"R2C" not in n.name.components, self.awaiting_data))
        if len(l) == 0:
            return True
        else:
            return False

    def ageing(self) -> List[Name]:
        """Age the entries inside the list awaiting data
        :return A list of entries for which timeout reqests must be sent and [] if reqest is fine, None if entry must be deleted
        """
        ts = time.time()
        #Rewrite Case
        if self.comp_state == NFNComputationState.REWRITE: #TODO this contains a code duplication with handleNack in BasicNFNLayer
            if self.awaiting_data != [] and ts > self.awaiting_data[0].time_stamp + self.timeout:  #r2c msg timout
                self.rewrite_list.pop(0)
                if self.rewrite_list == []:
                    return None
            if ts > self.time_stamp + self.timeout:
                r2c_request = self.r2cclient.R2C_create_message(self.rewrite_list[0])
                self.add_name_to_await_list(r2c_request)
                request_name = self.parser.nfn_str_to_network_name(self.rewrite_list[0])
                return [request_name, r2c_request]
            else:
                return []
        #Local Case
        possible_requests = []
        for al_entry in self.awaiting_data:
            if ts > self.timeout + al_entry.time_stamp:
                if self.r2cclient.R2C_identify_Name(al_entry.name):
                    return None
                possible_requests.append(al_entry.name)
        required_requests = self.r2cclient.R2C_selection(possible_requests)
        if required_requests == None:
            return None
        for name in required_requests:
            al_entry = list(filter(lambda n: n.name == name, self.awaiting_data))[0]
            self.awaiting_data.remove(al_entry)
            al_entry.times = time.time()
            self.awaiting_data.append(al_entry)
        r2c_requests = list(map(lambda n: self.r2cclient.R2C_create_message(n), required_requests))
        for r2c_r in r2c_requests:
            self.add_name_to_await_list(r2c_r)
        return required_requests + r2c_requests

    def __eq__(self, other):
        return self.original_name == other.original_name


class BaseNFNComputationTable(object):
    """BaseNFNComputationTable to handle running computations
    :param r2cclient: R2CClient to handle ageing
    """

    def __init__(self, r2cclient: BaseR2CHandler, parser: DefaultNFNParser):
        self.r2cclient = r2cclient
        self.parser = parser
        self.container: List[NFNComputationTableEntry] = []

    @abc.abstractmethod
    def add_computation(self, name: Name, id: int, interest: Interest, ast: AST=None) -> bool:
        """add a computation to the Computation table (i.e. start a new computation)
        :param name: icn-name of the computation
        :param id: ID given from layer communication
        :param interest: the original interest message
        :param AST: abstract syntax tree of the computation
        :return True if entry was added, false if it was already available and timestamp was updated
        """

    @abc.abstractmethod
    def is_comp_running(self, name: Name) -> bool:
        """checks if a name was already added to the list of running computations
        :param name: name to check
        :return True if computation was already added, else false
        """

    @abc.abstractmethod
    def get_computation(self, name: Name) -> NFNComputationTableEntry:
        """Find a NFNComputationTableEntry
        :param name: Name of the computation for which a Entry should be returned
        :return The NFNComputationEntry corresponding to the name
        """

    @abc.abstractmethod
    def remove_computation(self, name: Name):
        """Removes a NFNComputationEntry from the container
        :param name: Name of the Computation to be removed
        """

    @abc.abstractmethod
    def append_computation(self, entry: NFNComputationTableEntry):
        """Appends a NFNComputationTableEntry if it is not already available in the container
        :param entry: the NFNComputationTableEntry to be appended
        """

    @abc.abstractmethod
    def push_data(self, content: Content) -> bool:
        """add received data to running computations
        :param content: content to be added
        :return True if the content was required, else False
        """

    @abc.abstractmethod
    def get_ready_computations(self) -> List[NFNComputationTableEntry]:
        """get all computations that are ready to continue
        :return List of all NFNComputationTableEntrys which are ready
        """

    @abc.abstractmethod
    def ageing(self) -> (List[Name], List[NFNComputationTableEntry]):
        """age the running computations.
        Removes entries which timed out and tells for which entries a timeout request must be sent
        :return List of Names for which Timeout Reqest must be sent and List of NFNComputationTableEntrys for which nacks must be sent.
        """

    def update_status(self, name: Name, status: NFNComputationState):
        """Update the status of a computation giving a name
        :param name: Name of the computation entry to be updated
        :param status: The new Status
        """
        c = self.get_computation(name)
        self.remove_computation(name)
        c.comp_state = status
        self.append_computation(c)

    def add_awaiting_data(self, name: Name, awaiting_name: Name):
        """Add a name to the await list of a existing computation
        :param name: Name of the existing computation
        "param awaiting_name: Name to be added to the await list.
        """
        c = self.get_computation(name)
        self.remove_computation(name)
        c.add_name_to_await_list(awaiting_name)
        self.append_computation(c)
