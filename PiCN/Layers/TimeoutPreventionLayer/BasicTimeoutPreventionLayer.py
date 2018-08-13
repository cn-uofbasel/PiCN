"""BasicR2CLayer maintains a list of messages for which R2C messages should be sent.
Moreover, it contains handler for incomming R2C messages"""

import multiprocessing
import time

from typing import Dict

from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Nack, NackReason, Name

class TimeoutPreventionMessageDict(object):
    """Datastructure, that contains R2C messages and the matching handlers"""

    def __init__(self):
        self.container: Dict[Name, TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry] = {}

    class TimeoutPreventionMessageDictEntry(object):
        def __init__(self):
            self.timestamp = time.time()


    def get_entry(self, name: Name) -> TimeoutPreventionMessageDictEntry:
        """search for an entry in the Dict
        :param name: name of the entry
        :return entry if found, else None
        """
        return self.container.get(name)

    def add_entry(self, name: Name, entry: TimeoutPreventionMessageDictEntry):
        """add an entry to the dict
        :param name: Name of the Entry
        :param entry: the entry itself
        """
        self.container.update(name, entry)

    def update_timestamp(self, name: Name):
        """set the timestamp of the corresponding entry to time.time()
        :param name: Name of the Entry to be updated
        """
        entry = self.container.get(name)
        if entry is not None:
            del self.container[name]
        entry.timestamp = time.time()
        self.container.update(name, entry)

    def remove_entry(self, name):
        """Remove an entry from the dict
        :param name: name of the entry to be removed
        """
        if name in self.container:
            del self.container[name]

class BasicTimeoutPreventionLayer(LayerProcess):
    """BasicR2CLayer maintains a list of messages for which R2C messages should be sent.
    Moreover, it contains handler for incomming R2C messages"""

    def __init__(self, message_dict: TimeoutPreventionMessageDict):
        self.message_dict = message_dict

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        packet_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            to_higher.put(data)
        elif isinstance(packet, Content) or isinstance(packet, Nack):
            entry = self.message_dict.get_entry(packet.name)
            if entry is None:
                return
            self.message_dict.remove_entry(packet.name)
            to_higher.put(data)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        packet_id = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            pass #todo add interest to the handler list
        else:
            to_lower.put(data)


