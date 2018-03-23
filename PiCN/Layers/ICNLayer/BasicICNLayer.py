"""Basic ICN Forwarding Layer. Calls Functions that handles the ICN Forwarding"""

import multiprocessing
import threading
import time
from typing import List

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, ForwardingInformationBaseEntry

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable, PendingInterestTableEntry
from PiCN.Packets import Name, Content, Interest, Packet, Nack, NackReason
from PiCN.Processes import LayerProcess


class BasicICNLayer(LayerProcess):
    """ICN Forwarding Plane. Maintains data structures for ICN Forwarding"""

    def __init__(self, cs: BaseContentStore=None, pit: BasePendingInterestTable =None,
                 fib: BaseForwardingInformationBase=None, log_level=255):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        self._cs: BaseContentStore = cs
        self._pit: BasePendingInterestTable = pit
        self._fib: BaseContentStore = fib
        self._cs_timeout: int = 10
        self._pit_timeout: int = 10
        self._pit_retransmits: int = 3
        self._ageing_interval: int = 4
        self._interest_to_app: bool = False

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        highlevelid = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            cs_entry = self._cs.find_content_object(packet.name)
            if cs_entry is not None:
                self.queue_to_higher.put([highlevelid, cs_entry.content])
                return
            pit_entry = self._pit.find_pit_entry(packet.name)
            self._pit.add_pit_entry(packet.name, highlevelid, packet, local_app=True)
            fib_entry = self._fib.find_fib_entry(packet.name)
            if fib_entry is not None:
                self._pit.add_used_fib_entry(packet.name, fib_entry)
                to_lower.put([fib_entry.faceid, packet])
            else:
                self.logger.info("No FIB entry, sending Nack")
                nack = Nack(packet.name, NackReason.NO_ROUTE, interest=packet)
                if pit_entry is not None: #if pit entry is available, consider it, otherwise assume interest came from higher
                    for i in range(0, len(pit_entry.faceids)):
                        if pit_entry._local_app[i]:
                            to_higher.put([highlevelid, nack])
                        else:
                            to_lower.put([pit_entry._faceids[i], nack])
                else:
                    to_higher.put([highlevelid, nack])
        elif isinstance(packet, Content):
            self.handleContent(highlevelid, packet, to_lower, to_higher, True) #content handled same as for content from network
        elif isinstance(packet, Nack):
            self.handleNack(highlevelid, packet, to_lower, to_higher, True) #Nack handeled same as for nack from network

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        if len(data) != 2:
            self.logger.warning("ICN Layer expects to receive [face id, packet] from lower layer")
            return
        if type(data[0]) != int:
            self.logger.warning("ICN Layer expects to receive [face id, packet] from lower layer")
            return
        if not isinstance(data[1], Packet):
            self.logger.warning("ICN Layer expects to receive [face id, packet] from lower layer")
            return

        faceid = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.handleInterest(faceid, packet, to_lower, to_higher, False)
        elif isinstance(packet, Content):
            self.handleContent(faceid, packet, to_lower, to_higher, False)
        elif isinstance(packet, Nack):
            self.handleNack(faceid, packet, to_lower, to_higher, False)

    def handleInterest(self, faceid: int, interest: Interest, to_lower: multiprocessing.Queue,
                       to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling Interest")
        #if to_higher is not None: #TODO check if app layer accepted the data, and change handling

        cs_entry = self.check_cs(interest)
        if cs_entry is not None:
            self.logger.info("Found in content store")
            to_lower.put([faceid, cs_entry.content])
            self._cs.update_timestamp(cs_entry)
            return
        pit_entry = self.check_pit(interest.name)
        if pit_entry is not None:
            self.logger.info("Found in PIT, apending")
            self._pit.update_timestamp(pit_entry)
            self._pit.add_pit_entry(interest.name, faceid, interest, local_app=from_local)
            return
        if self._interest_to_app is True and to_higher is not None: #App layer support
            self.logger.info("Sending to higher Layer")
            self._pit.add_pit_entry(interest.name, faceid, interest, local_app=from_local)
            self.queue_to_higher.put([faceid, interest])
            return
        newfaceid = self.check_fib(interest.name, None)
        if newfaceid is not None:
            self.logger.info("Found in FIB, forwarding")
            self._pit.add_pit_entry(interest.name, faceid, interest ,local_app=from_local)
            self._pit.add_used_fib_entry(interest.name, newfaceid)
            to_lower.put([newfaceid.faceid, interest])
            return
        self.logger.info("No FIB entry, sending Nack")
        nack = Nack(interest.name, NackReason.NO_ROUTE, interest=interest)
        if from_local:
            to_higher.put([faceid, nack])
        else:
            to_lower.put([faceid, nack])

    def handleContent(self, faceid: int, content: Content, to_lower: multiprocessing.Queue,
                       to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling Content " + str(content.name) + " " + str(content.content))
        pit_entry = self.check_pit(content.name)
        if pit_entry is None:
            self.logger.info("No PIT entry for content object available, dropping")
            #todo NACK??
            return
        else:
            for i in range(0, len(pit_entry.faceids)):
                if to_higher and pit_entry.local_app[i]:
                    to_higher.put([faceid, content])
                else:
                    to_lower.put([pit_entry.faceids[i], content])
            self._pit.remove_pit_entry(pit_entry.name)
            self._cs.add_content_object(content)

    def handleNack(self, faceid: int, nack: Nack, to_lower: multiprocessing.Queue,
                       to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling Nack")
        pit_entry = self.check_pit(nack.name)
        if pit_entry is None:
            self.logger.info("No PIT entry for Nack available, dropping")
            return
        else:
            fib_entry = self.check_fib(nack.name, pit_entry.fib_entries_already_used)
            if fib_entry is None:
                self.logger.info("Sending Nack to previous node(s)")
                re_add = False
                for i in range(0, len(pit_entry.faceids)):
                    if pit_entry.local_app[i] == True: #Go with nack first only to app layer if it was requested
                        re_add = True
                self._pit.remove_pit_entry(pit_entry.name)
                for i in range(0, len(pit_entry.faceids)):
                    if to_higher and pit_entry.local_app[i]:
                        to_higher.put([faceid, nack])
                        del pit_entry.face_id[i]
                        del pit_entry.local_app[i]
                    elif not re_add:
                        to_lower.put([pit_entry.faceids[i], nack])
                if re_add:
                    self._pit.container.append(pit_entry)
            else:
                self.logger.info("Try using next FIB path")
                self._pit.add_used_fib_entry(nack.name, fib_entry)
                to_lower.put([fib_entry.faceid, pit_entry.interest])


    def ageing(self):
        """Ageing the datastructs"""
        try:
            self.logger.debug("Ageing")
            self.pit_ageing()
            self.cs_ageing()
            t = threading.Timer(self._ageing_interval, self.ageing)
            t.setDaemon(True)
            t.start()
        except:
            pass

    def pit_ageing(self):
        """Agieing the PIT"""
        cur_time = time.time()
        remove = []
        updated = []
        for pit_entry in self._pit.container:
            if pit_entry.timestamp + self._pit_timeout < cur_time \
                    and pit_entry.retransmits > self._pit_retransmits:
                remove.append(pit_entry)
            else:
                pit_entry.retransmits = pit_entry.retransmits + 1
                updated.append(pit_entry)
                newfaceid = self.check_fib(pit_entry.name, pit_entry.fib_entries_already_used)
                if newfaceid is not None:
                    self.queue_to_lower.put([newfaceid.faceid, pit_entry.interest])
        for pit_entry in remove:
            self._pit.remove_pit_entry(pit_entry.name)
        for pit_entry in updated:
            self._pit.remove_pit_entry(pit_entry.name)
            self._pit.container.append(pit_entry)

    def cs_ageing(self):
        """Aging the CS"""
        cur_time = time.time()
        remove = []
        for cs_entry in self._cs.container:
            if cs_entry.static is True:
                continue
            if cs_entry.timestamp + self._cs_timeout < cur_time:
                remove.append(cs_entry)
        for cs_entry in remove:
            self._cs.remove_content_object(cs_entry.content.name)


    def check_cs(self, interest: Interest) -> Content:
        return self._cs.find_content_object(interest.name)

    def check_pit(self, name: Name) -> PendingInterestTableEntry:
        return self._pit.find_pit_entry(name)

    def check_fib(self, name: Name, alreadused: List[ForwardingInformationBaseEntry]) \
            -> ForwardingInformationBaseEntry:
        return  self._fib.find_fib_entry(name, already_used=alreadused)

    @property
    def cs(self):
        """The Content Store"""
        return self._cs

    @cs.setter
    def cs(self, cs):
        self._cs = cs

    @property
    def fib(self):
        """The Forwarding Information Base"""
        return self._fib

    @fib.setter
    def fib(self, fib):
        self._fib = fib

    @property
    def pit(self):
        """The Pending Interest Table"""
        return self._pit

    @pit.setter
    def pit(self, pit):
        self._pit = pit
