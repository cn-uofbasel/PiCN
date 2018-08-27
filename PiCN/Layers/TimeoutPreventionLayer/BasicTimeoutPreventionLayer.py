"""BasicR2CLayer maintains a list of messages for which R2C messages should be sent.
Moreover, it contains handler for incomming R2C messages"""

import multiprocessing
import time, threading

from typing import Dict

from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable

class TimeoutPreventionMessageDict(object):
    """Datastructure, that contains R2C messages and the matching handlers"""

    def __init__(self):
        self.container: Dict[Name, TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry] = {}

    class TimeoutPreventionMessageDictEntry(object):
        """Datastructure Entry"""
        def __init__(self, packetid):
            self.timestamp = time.time()
            self.packetid = packetid


    def get_entry(self, name: Name) -> TimeoutPreventionMessageDictEntry:
        """search for an entry in the Dict
        :param name: name of the entry
        :return entry if found, else None
        """
        if name in self.container:
            return self.container.get(name)

    def add_entry(self, name: Name, entry: TimeoutPreventionMessageDictEntry):
        """add an entry to the dict
        :param name: Name of the Entry
        :param entry: the entry itself
        """
        self.container[name] = entry

    def create_entry(self, name: Name, packet_id: int):
        """create an new entry given a name
        :param name: name for the entry
        """
        entry = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(packet_id)
        self.add_entry(name, entry)

    def update_timestamp(self, name: Name):
        """set the timestamp of the corresponding entry to time.time()
        :param name: Name of the Entry to be updated
        """
        entry = self.container.get(name)
        if entry is not None:
            self.remove_entry(name)
        else:
            return
        entry_n = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(entry.packetid)
        self.add_entry(name, entry_n)

    def remove_entry(self, name):
        """Remove an entry from the dict
        :param name: name of the entry to be removed
        """
        if name in self.container:
            del self.container[name]

    def get_container(self):
        return self.container

class BasicTimeoutPreventionLayer(LayerProcess):
    """BasicR2CLayer maintains a list of messages for which R2C messages should be sent.
    Moreover, it contains handler for incomming R2C messages"""

    def __init__(self, message_dict: TimeoutPreventionMessageDict, nfn_comp_table: BaseNFNComputationTable, log_level = 255):
        super().__init__("TimeoutPrev", log_level)
        self.timeout_interval = 2
        self.ageing_interval = 1
        self.message_dict = message_dict
        self.computation_table = nfn_comp_table
        self.running_computations = [] #todo, this field is required because computation table does not sync fast enough. is this correct, fix BaseMangager access.

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        packet_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.logger.info("Reveived Interest from lower... " + str(packet.name))
            if len(packet.name.components) > 2 and packet.name.string_components[-2] == 'KEEPALIVE':
                self.logger.info("Interest is keep alive")
                if self.computation_table is None:
                    return
                nfn_name = self.remove_keep_alive_from_name(packet.name)
                self.logger.info("NFN name is: " + str(nfn_name))
                self.logger.info("#Running Computations: " + str(self.computation_table.is_comp_running(nfn_name)))
                comp = self.computation_table.get_computation(nfn_name)
                if comp is not None or self.computation_table.is_comp_running(nfn_name) or nfn_name in self.running_computations:
                    to_lower.put([packet_id, Content(packet.name)])
                else:
                    to_lower.put([packet_id, Nack(packet.name, NackReason.COMP_NOT_RUNNING, interest=packet)]) #todo is it working with a nack?
                return
            elif len(packet.name.components) > 0 and packet.name.components[-1] == b'NFN':
                self.running_computations.append(packet.name)
                to_higher.put(data)
            else:
                to_higher.put(data)
        elif (isinstance(packet, Content) or isinstance(packet, Nack)) and len(packet.name.components) > 2 and packet.name.string_components[-2] == 'KEEPALIVE':
            if isinstance(packet, Content):
                self.logger.info("Received KEEP ALIVE reply, updating timestamps")
                self.message_dict.update_timestamp(packet.name) #update timestamp for the R2C message
                return
            if isinstance(packet, Nack):
                original_name = self.remove_keep_alive_from_name(packet.name)
                self.message_dict.remove_entry(packet.name)
                self.message_dict.remove_entry(original_name)
                self.queue_to_higher.put([packet_id, Nack(original_name, reason=NackReason.COMP_NOT_RUNNING,
                                                          interest=Interest(original_name))])
        elif isinstance(packet, Content) or isinstance(packet, Nack): #R2C Content or Nack, remove entry and give to higher layer
            entry = self.message_dict.get_entry(packet.name)
            if entry is not None:
                self.logger.info("Removing entry from Keep Alive Dict")
                self.message_dict.remove_entry(packet.name)
                keepalive_name = self.add_keep_alive_from_name(packet.name)
                self.message_dict.remove_entry(keepalive_name)
            to_higher.put(data) #TODO R2C nack not handled correctly?

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        packet_id = data[0]
        packet = data[1]
        try:
            self.running_computations.remove(packet.name)
        except:
            pass
        self.logger.info("Received Packet from higher")
        if isinstance(packet, Interest) and packet.name.string_components[-1] == "NFN":
            self.logger.info("Packet is NFN interest, start timeout prevention")
            keepalive_name = self.add_keep_alive_from_name(packet.name)
            self.message_dict.create_entry(name=packet.name, packet_id=packet_id)
            self.message_dict.create_entry(name=keepalive_name, packet_id=packet_id)
        to_lower.put(data)

    def ageing(self):
        if self.queue_to_lower._closed or self.queue_to_higher._closed:
            return
        try:
            removes = []
            container = self.message_dict.get_container()
            for name in container:
                entry = self.message_dict.get_entry(name)
                if len(name.components) > 2 and name.string_components[-2] == "KEEPALIVE":
                    if entry.timestamp + self.timeout_interval < time.time():
                        self.logger.info("Remove Keep Alvie Job because of timeout")
                        removes.append(name)
                        self.running_computations.remove(name)
                        original_name = self.remove_keep_alive_from_name(name)
                        removes.append(original_name)
                        self.running_computations.remove(original_name)
                        nack = Nack(name=original_name, reason=NackReason.COMP_NOT_RUNNING, interest=Interest(name))
                        self.queue_to_higher.put([entry.packetid, nack]) #TODO ID
                    else:
                        self.queue_to_lower.put([entry.packetid, Interest(name=name)])
                else:
                    self.queue_to_lower.put([entry.packetid, Interest(name=name)])
            for n in removes:
                self.message_dict.remove_entry(n)
        except Exception as e:
            self.logger.warning("Exception during ageing: " + str(e))
            return
        t = threading.Timer(self.ageing_interval, self.ageing)
        t.setDaemon(True)
        t.start()

    def add_keep_alive_from_name(self, name):
        if name.components[-1] != b"NFN":
            return name
        new_name = Name()
        for n in name.string_components:
            new_name += n
        new_name.components.remove(b"NFN")
        new_name += "KEEPALIVE"
        new_name += "NFN"
        return new_name

    def remove_keep_alive_from_name(self, name):
        if name.components[-1] != b"NFN":
            return name
        new_name = Name()
        for n in name.string_components:
            new_name += n
        new_name.components.remove(b"KEEPALIVE")
        return new_name
