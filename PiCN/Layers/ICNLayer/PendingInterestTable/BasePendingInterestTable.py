"""Abstract BasePendingInterestTable for usage in BasicICNLayer"""

import abc
import multiprocessing
import time
from typing import List

from PiCN.Packets import Interest, Name
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseEntry
from PiCN.Layers.ICNLayer import BaseICNDataStruct


class PendingInterestTableEntry(object):
    """An entry in the Forwarding Information Base"""

    def __init__(self, name: Name, faceid: int, interest: Interest = None, local_app: bool = False):
        self.name = name
        self._faceids: List[int] = []
        if isinstance(faceid, list):
            self._faceids = faceid
        else:
            self._faceids.append(faceid)
        self._timestamp = time.time()
        self._retransmits = 0
        self._local_app: List[bool] = []
        if isinstance(local_app, list):
            self._local_app.extend(local_app)
        else:
            self._local_app.append(local_app)
        self._interest = interest
        self._fib_entries_already_used: List[ForwardingInformationBaseEntry] = []

    def __eq__(self, other):
        if other is None:
            return False
        return self.name == other.name

    @property
    def interest(self):
        return self._interest

    @interest.setter
    def interest(self, interest):
        self._interest = interest

    @property
    def faceids(self):
        return self._faceids

    @faceids.setter
    def face_id(self, faceids):
        self._faceids = faceids

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp

    @property
    def retransmits(self):
        return self._retransmits

    @retransmits.setter
    def retransmits(self, retransmits):
        self._retransmits = retransmits

    @property
    def local_app(self):
        return self._local_app

    @local_app.setter
    def local_app(self, local_app):
        self._local_app = local_app

    @property
    def interest(self):
        return self._interest

    @interest.setter
    def interest(self, interest):
        self._interest = interest

    @property
    def fib_entries_already_used(self):
        return self._fib_entries_already_used

    @fib_entries_already_used.setter
    def fib_entries_already_used(self, fib_entries_already_used):
        self._fib_entries_already_used = fib_entries_already_used


class BasePendingInterestTable(BaseICNDataStruct):
    """Abstract BasePendingInterestaTable for usage in BasicICNLayer
    :param pit_timeout: timeout for a pit entry when calling the ageing function
    """

    def __init__(self, pit_timeout: int = 10, pit_retransmits: int = 3):
        super().__init__()
        self.container: List[PendingInterestTableEntry] = []
        self._pit_timeout = pit_timeout
        self._pit_retransmits = pit_retransmits

    @abc.abstractmethod
    def add_pit_entry(self, name: Name, faceid: int, interest: Interest = None, local_app: bool = False):
        """Add an new entry"""

    @abc.abstractmethod
    def find_pit_entry(self, name: Name) -> PendingInterestTableEntry:
        """Find an entry in the PIT"""

    @abc.abstractmethod
    def remove_pit_entry(self, name: Name):
        """Remove an entry in the PIT"""

    @abc.abstractmethod
    def update_timestamp(self, pit_entry: PendingInterestTableEntry):
        """Update Timestamp of a PIT Entry"""

    @abc.abstractmethod
    def add_used_fib_entry(self, name: Name, used_fib_entry: ForwardingInformationBaseEntry):
        """Add a used fib entry to the already used fib entries"""

    @abc.abstractmethod
    def ageing(self) -> List[PendingInterestTableEntry]:
        """Update the entries periodically
        :return List of PIT entries to be retransmitted
        """

    @abc.abstractmethod
    def append(self, entry):
        """append an pit_entry to the pit container
        :param entry: entry to be appended
        """

    @abc.abstractmethod
    def get_already_used_pit_entries(self, name: Name):
        """Get already used fib entries"""

    def set_pit_timeout(self, timeout: float):
        """set the timeout intervall for a pit entry
        :param timeout: timout value to be set
        """
        self._pit_timeout = timeout

    def set_pit_retransmits(self, retransmits: int):
        """set the max number of retransmits for a pit entry
        :param retransmits: retransmit value to be set
        """
        self._pit_retransmits = retransmits
