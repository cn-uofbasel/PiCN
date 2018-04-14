"""Basic ICN Forwarding Layer"""

import multiprocessing
import threading
import time
from typing import List

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, ForwardingInformationBaseEntry
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable, PendingInterestTableEntry
from PiCN.Packets import Name, Content, Interest, Packet, Nack, NackReason
from PiCN.Processes import LayerProcess


class BasicICNLayer(LayerProcess):
    """ICN Forwarding Plane. Maintains data structures for ICN Forwarding
    """

    def __init__(self, cs: BaseContentStore=None, pit: BasePendingInterestTable=None,
                 fib: BaseForwardingInformationBase=None, log_level=255, manager: multiprocessing.Manager=None):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        if manager is None:
            manager = multiprocessing.Manager()
        # Store CS, FIB, PIT here to sync over processes.
        # Note: Datastruct must be stored in a local var to access and be written back to the dict to sync!
        self._data_structs = manager.dict()
        self._data_structs['cs'] = cs
        self._data_structs['pit'] = pit
        self._data_structs['fib'] = fib
        self._cs_timeout: int = 10
        self._pit_timeout: int = 10
        self._pit_retransmits: int = 3
        self._ageing_interval: int = 4
        self._interest_to_app: bool = False

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        high_level_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            cs_entry = self.check_cs(packet)
            if cs_entry is not None:
                self.queue_to_higher.put([high_level_id, cs_entry.content])
                return
            pit_entry = self.pit.find_pit_entry(packet.name)
            self.add_to_pit(packet.name, high_level_id, packet, local_app=True)
            fib_entry = self.fib.find_fib_entry(packet.name)
            if fib_entry is not None:
                self.add_used_fib_entry_to_pit(packet.name, fib_entry)
                to_lower.put([fib_entry.faceid, packet])
            else:
                self.logger.info("No FIB entry, sending Nack")
                nack = Nack(packet.name, NackReason.NO_ROUTE, interest=packet)
                if pit_entry is not None: #if pit entry is available, consider it, otherwise assume interest came from higher
                    for i in range(0, len(pit_entry.faceids)):
                        if pit_entry._local_app[i]:
                            to_higher.put([high_level_id, nack])
                        else:
                            to_lower.put([pit_entry._faceids[i], nack])
                else:
                    to_higher.put([high_level_id, nack])
        elif isinstance(packet, Content):
            self.handle_content(high_level_id, packet, to_lower, to_higher, True) #content handled same as for content from network
        elif isinstance(packet, Nack):
            self.handle_nack(high_level_id, packet, to_lower, to_higher, True) #Nack handled same as for NACK from network

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

        face_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.handle_interest(face_id, packet, to_lower, to_higher, False)
        elif isinstance(packet, Content):
            self.handle_content(face_id, packet, to_lower, to_higher, False)
        elif isinstance(packet, Nack):
            self.handle_nack(face_id, packet, to_lower, to_higher, False)

    def handle_interest(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue,
                        to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling Interest")
        #if to_higher is not None: #TODO check if app layer accepted the data, and change handling

        cs_entry = self.check_cs(interest)
        if cs_entry is not None:
            self.logger.info("Found in content store")
            to_lower.put([face_id, cs_entry.content])
            self.update_timestamp_in_cs(cs_entry)
            return
        pit_entry = self.check_pit(interest.name)
        if pit_entry is not None:
            self.logger.info("Found in PIT, appending")
            self.update_timestamp_in_pit(pit_entry)
            self.add_to_pit(interest.name, face_id, interest, local_app=from_local)
            return
        if self._interest_to_app is True and to_higher is not None: #App layer support
            self.logger.info("Sending to higher Layer")
            self.add_to_pit(interest.name, face_id, interest, local_app=from_local)
            self.queue_to_higher.put([face_id, interest])
            return
        new_face_id = self.check_fib(interest.name, None)
        if new_face_id is not None:
            self.logger.info("Found in FIB, forwarding")
            self.add_to_pit(interest.name, face_id, interest, local_app=from_local)
            self.add_used_fib_entry_to_pit(interest.name, new_face_id)
            to_lower.put([new_face_id.faceid, interest])
            return
        self.logger.info("No FIB entry, sending Nack")
        nack = Nack(interest.name, NackReason.NO_ROUTE, interest=interest)
        if from_local:
            to_higher.put([face_id, nack])
        else:
            to_lower.put([face_id, nack])

    def handle_content(self, face_id: int, content: Content, to_lower: multiprocessing.Queue,
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
                    to_higher.put([face_id, content])
                else:
                    to_lower.put([pit_entry.faceids[i], content])
            self.remove_pit_entry(pit_entry.name)
            self.add_to_cs(content)

    def handle_nack(self, face_id: int, nack: Nack, to_lower: multiprocessing.Queue,
                    to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling NACK")
        pit_entry = self.check_pit(nack.name)
        if pit_entry is None:
            self.logger.info("No PIT entry for NACK available, dropping")
            return
        else:
            fib_entry = self.check_fib(nack.name, pit_entry.fib_entries_already_used)
            if fib_entry is None:
                self.logger.info("Sending NACK to previous node(s)")
                re_add = False
                for i in range(0, len(pit_entry.faceids)):
                    if pit_entry.local_app[i] == True: #Go with NACK first only to app layer if it was requested
                        re_add = True
                self.remove_pit_entry(pit_entry.name)
                for i in range(0, len(pit_entry.faceids)):
                    if to_higher and pit_entry.local_app[i]:
                        to_higher.put([face_id, nack])
                        del pit_entry.face_id[i]
                        del pit_entry.local_app[i]
                    elif not re_add:
                        to_lower.put([pit_entry.faceids[i], nack])
                if re_add:
                    pit = self.pit
                    pit.container.append(pit_entry)
                    self.pit = pit
            else:
                self.logger.info("Try using next FIB path")
                self.add_used_fib_entry_to_pit(nack.name, fib_entry)
                to_lower.put([fib_entry.faceid, pit_entry.interest])

    def ageing(self):
        """Ageing the data structs"""
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
        """Ageing the PIT"""
        cur_time = time.time()
        remove = []
        updated = []
        for pit_entry in self.pit.container:
            if pit_entry.timestamp + self._pit_timeout < cur_time and pit_entry.retransmits > self._pit_retransmits:
                remove.append(pit_entry)
            else:
                pit_entry.retransmits = pit_entry.retransmits + 1
                updated.append(pit_entry)
                new_face_id = self.check_fib(pit_entry.name, pit_entry.fib_entries_already_used)
                if new_face_id is not None:
                    self.queue_to_lower.put([new_face_id.faceid, pit_entry.interest])
        for pit_entry in remove:
            self.remove_pit_entry(pit_entry.name)
        for pit_entry in updated:
            self.remove_pit_entry(pit_entry.name)
            pit = self.pit
            pit.container.append(pit_entry)
            self.pit = pit

    def cs_ageing(self):
        """Aging the CS"""
        cur_time = time.time()
        remove = []
        cs = self.cs
        for cs_entry in cs.container:
            if cs_entry.static is True:
                continue
            if cs_entry.timestamp + self._cs_timeout < cur_time:
                remove.append(cs_entry)
        for cs_entry in remove:
            cs.remove_content_object(cs_entry.content.name)
        self.cs = cs

    def add_to_cs(self, content: Content, static=False):
        """Add an entry to the Content Store
        :param content: Content Object to be added
        :param static: If True, content will not be removed from CS by timeout
        """
        cs = self.cs
        cs.add_content_object(content, static)
        self.cs = cs

    def add_to_pit(self, name: Name, faceid: int, interest: Interest, local_app: bool):
        """Add an entry to the PIT
        :param name: Name of the PIT entry
        :param faceid: Faceid the PIT entry should point to (required to route the content back on its trace)
        :param interest: The original interest message
        :param local_app: indicates if the request was issued by a higher layer
        """
        pit = self.pit
        pit.add_pit_entry(name, faceid, interest, local_app)
        self.pit = pit

    def add_to_fib(self, name: Name, to_faceid: int, static: bool=False):
        """Add en entry to the FIB
        :param name: Name to match the FIB entry
        :param to_faceid: Face ID of the FIB entry
        :param static: Optional, if True, FIB entry is persistent
        """
        fib = self.fib
        fib.add_fib_entry(name, to_faceid, static)
        self.fib = fib

    def remove_pit_entry(self, name: Name):
        """Remove an entry from the PIT
        :param name: Name to identify the PIT entry to be removed
        """
        pit = self.pit
        pit.remove_pit_entry(name)
        self.pit = pit

    def add_used_fib_entry_to_pit(self, name: Name, used_fib_entry: ForwardingInformationBaseEntry):
        """Add a entry to the pit, that indicates that a certain forwarding rule was already used
        :param name: Name is used to identify the PIT entry
        :param used_fib_entry: the FIB entry that was used for the forwarding process
        """
        pit = self.pit
        pit.add_used_fib_entry(name, used_fib_entry)
        self.pit = pit

    def update_timestamp_in_cs(self, cs_entry: ContentStoreEntry):
        """update the timestamp of an CS entry
        :param cs_entry: The CS entry to be updated
        """
        cs = self.cs
        cs.update_timestamp(cs_entry)
        self.cs = cs

    def update_timestamp_in_pit(self, pit_entry: PendingInterestTableEntry):
        """update the timestamp of an PIT entry
        :param pit_entry: to be updated
        """
        pit = self.pit
        pit.update_timestamp(pit_entry)
        self.pit = pit

    def check_cs(self, interest: Interest) -> Content:
        return self.cs.find_content_object(interest.name)

    def check_pit(self, name: Name) -> PendingInterestTableEntry:
        return self.pit.find_pit_entry(name)

    def check_fib(self, name: Name, already_used: List[ForwardingInformationBaseEntry]) -> ForwardingInformationBaseEntry:
        return self.fib.find_fib_entry(name, already_used=already_used)

    @property
    def cs(self) -> BaseContentStore:
        """The Content Store"""
        return self._data_structs.get('cs')

    @cs.setter
    def cs(self, cs: BaseContentStore):
        self._data_structs['cs'] = cs

    @property
    def fib(self) -> BaseForwardingInformationBase:
        """The Forwarding Information Base"""
        return self._data_structs.get('fib')

    @fib.setter
    def fib(self, fib: BaseForwardingInformationBase):
        self._data_structs['fib'] = fib

    @property
    def pit(self) -> BasePendingInterestTable:
        """The Pending Interest Table"""
        return self._data_structs.get('pit')

    @pit.setter
    def pit(self, pit: BasePendingInterestTable):
        self._data_structs['pit'] = pit
