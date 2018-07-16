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
                 fib: BaseForwardingInformationBase=None, log_level=255):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        self.cs = cs
        self.pit = pit
        self.fib = fib
        self._ageing_interval: int = 4
        self._interest_to_app: bool = False

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        high_level_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            cs_entry = self.cs.find_content_object(packet.name)
            if cs_entry is not None:
                self.queue_to_higher.put([high_level_id, cs_entry.content])
                return
            pit_entry = self.pit.find_pit_entry(packet.name)
            self.pit.add_pit_entry(packet.name, high_level_id, packet, local_app=True)
            if pit_entry:
                fib_entry = self.fib.find_fib_entry(packet.name, incoming_faceids=pit_entry.face_id)
            else:
                fib_entry = self.fib.find_fib_entry(packet.name)
            if fib_entry is not None:
                self.pit.add_used_fib_entry(packet.name, fib_entry)
                to_lower.put([fib_entry.faceid, packet])
            else:
                self.logger.info("No FIB entry, sending Nack")
                nack = Nack(packet.name, NackReason.NO_ROUTE, interest=packet)
                if pit_entry is not None: #if pit entry is available, consider it, otherwise assume interest came from higher
                    for i in range(0, len(pit_entry.faceids)):
                        if pit_entry._local_app[i]:
                            to_higher.put([high_level_id, nack])
                    #    else:
                    #       to_lower.put([pit_entry._faceids[i], nack])
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

        cs_entry = self.cs.find_content_object(interest.name)
        if cs_entry is not None:
            self.logger.info("Found in content store")
            to_lower.put([face_id, cs_entry.content])
            self.cs.update_timestamp(cs_entry)
            return
        pit_entry = self.pit.find_pit_entry(interest.name)
        if pit_entry is not None:
            self.logger.info("Found in PIT, appending")
            self.pit.update_timestamp(pit_entry)
            self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
            return
        if self._interest_to_app is True and to_higher is not None: #App layer support
            self.logger.info("Sending to higher Layer")
            self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
            self.queue_to_higher.put([face_id, interest])
            return
        new_face_id = self.fib.find_fib_entry(interest.name, None, [face_id])
        if new_face_id is not None:
            self.logger.info("Found in FIB, forwarding")
            self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
            #self.add_used_fib_entry_to_pit(interest.name, new_face_id) #disabled, should only be applied if nack is received.
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
        pit_entry = self.pit.find_pit_entry(content.name)
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
            self.pit.remove_pit_entry(pit_entry.name)
            self.cs.add_content_object(content)

    def handle_nack(self, face_id: int, nack: Nack, to_lower: multiprocessing.Queue,
                    to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling NACK")
        pit_entry = self.pit.find_pit_entry(nack.name)
        if pit_entry is None:
            self.logger.info("No PIT entry for NACK available, dropping")
            return
        else:
            fib_entry = self.fib.find_fib_entry(nack.name, pit_entry.fib_entries_already_used, pit_entry.faceids)
            if fib_entry is None:
                self.logger.info("Sending NACK to previous node(s)")
                re_add = False
                for i in range(0, len(pit_entry.faceids)):
                    if pit_entry.local_app[i] == True: #Go with NACK first only to app layer if it was requested
                        re_add = True
                self.pit.remove_pit_entry(pit_entry.name)
                indices_to_remove = []
                for i in range(0, len(pit_entry.faceids)):
                    if to_higher is not None and pit_entry.local_app[i]:
                        to_higher.put([face_id, nack])
                        indices_to_remove.append(i)
                    elif not re_add:
                        to_lower.put([pit_entry.faceids[i], nack])
                if re_add:
                    indices_to_remove_reverse = indices_to_remove[::-1]
                    for i in indices_to_remove_reverse:
                        del pit_entry.face_id[i]
                        del pit_entry.local_app[i]
                    self.pit.append(pit_entry)
            else:
                self.logger.info("Try using next FIB path")
                self.pit.add_used_fib_entry(nack.name, fib_entry)
                to_lower.put([fib_entry.faceid, pit_entry.interest])

    def ageing(self):
        """Ageing the data structs"""
        try:
            self.logger.debug("Ageing")
            #PIT ageing
            retransmits = self.pit.ageing()
            for pit_entry in retransmits:
                fib_entry = self.fib.find_fib_entry(pit_entry.name, pit_entry.fib_entries_already_used, pit_entry.faceids)
                if not fib_entry:
                    continue
                self.queue_to_lower.put([fib_entry.faceid, pit_entry.interest])
            #CS ageing
            self.cs.ageing()
        except Exception as e:
            self.logger.warn("Exception during ageing: " + str(e))
            pass
        finally:
            t = threading.Timer(self._ageing_interval, self.ageing)
            t.setDaemon(True)
            t.start()
