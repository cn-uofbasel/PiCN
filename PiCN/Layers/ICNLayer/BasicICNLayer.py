"""Basic ICN Forwarding Layer"""

import multiprocessing
import threading
import time
from typing import List

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, ForwardingInformationBaseEntry
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable, PendingInterestTableEntry
from PiCN.Packets import Name, Content, Interest, Packet, Nack, NackReason
from PiCN.Processes import LayerProcess


class BasicICNLayer(LayerProcess):
    """ICN Forwarding Plane. Maintains data structures for ICN Forwarding
    """

    def __init__(self, cs: BaseContentStore=None, pit: BasePendingInterestTable=None,
            fib: BaseForwardingInformationBase=None, rib: BaseRoutingInformationBase = None, log_level=255,
                 ageing_interval: int=3):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        self.cs = cs
        self.pit = pit
        self.fib = fib
        self.rib = rib
        self._ageing_interval: int = ageing_interval
        self._interest_to_app: bool = False

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        high_level_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.handle_interest_from_higher(high_level_id, packet, to_lower, to_higher)
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
        self.logger.info("Received Packet from lower: " + str(face_id) + "; " + str(packet.name))
        if isinstance(packet, Interest):
            self.handle_interest_from_lower(face_id, packet, to_lower, to_higher, False)
        elif isinstance(packet, Content):
            self.handle_content(face_id, packet, to_lower, to_higher, False)
        elif isinstance(packet, Nack):
            self.handle_nack(face_id, packet, to_lower, to_higher, False)

    def handle_interest_from_higher (self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue,
                                   to_higher: multiprocessing.Queue):
        self.logger.info("Handling Interest (from higher): " + str(interest.name) + "; Face ID: " + str(face_id))
        cs_entry = self.cs.find_content_object(interest.name)
        if cs_entry is not None:
            self.queue_to_higher.put([face_id, cs_entry.content])
            return
        pit_entry = self.pit.find_pit_entry(interest.name)
        self.pit.add_pit_entry(interest.name, face_id, interest, local_app=True)
        if pit_entry:
            fib_entry = self.fib.find_fib_entry(interest.name, incoming_faceids=pit_entry.faceids)
        else:
            fib_entry = self.fib.find_fib_entry(interest.name)
        if fib_entry is not None:
            self.pit.set_number_of_forwards(interest.name, 0)
            for fid in fib_entry.faceid:
                try:
                    if not self.pit.test_faceid_was_nacked(interest.name, fid):
                        self.pit.increase_number_of_forwards(interest.name)
                        to_lower.put([fid, interest])
                except:
                    pass
        else:
            self.logger.info("No FIB entry, sending Nack: " + str(interest.name))
            nack = Nack(interest.name, NackReason.NO_ROUTE, interest=interest)
            if pit_entry is not None:  # if pit entry is available, consider it, otherwise assume interest came from higher
                for i in range(0, len(pit_entry.faceids)):
                    if pit_entry._local_app[i]:
                        to_higher.put([face_id, nack])
                    else:
                        to_lower.put([pit_entry._faceids[i], nack])
            else:
                to_higher.put([face_id, nack])

    def handle_interest_from_lower(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue,
                                   to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling Interest (from lower): " + str(interest.name) + "; Face ID: " + str(face_id))
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
            self.logger.info("Found in FIB, forwarding to Face: " +  str(new_face_id.faceid))
            self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
            for fid in new_face_id.faceid:
                if not self.pit.test_faceid_was_nacked(interest.name, fid):
                    self.pit.increase_number_of_forwards(interest.name)
                    to_lower.put([fid, interest])
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
        self.logger.info("Handling NACK: " + str(nack.name) + " Reason: " + str(nack.reason) + ", From FaceID: " +
                         str(face_id) + ", From Local: " + str(from_local))
        cur_pit_entry = self.pit.find_pit_entry(nack.name)
        if cur_pit_entry is None:
            self.logger.info("No PIT entry for NACK available, dropping")
            return
        else:
            self.pit.add_nacked_faceid(nack.name, face_id)
            if cur_pit_entry.number_of_forwards > 1:
                self.logger.info("Ignoring Nack from FaceID " + str(face_id) + " for " + str(nack.name) + " since other faces (" + str(cur_pit_entry.number_of_forwards) + ") are still active")
                self.pit.decrease_number_of_forwards(nack.name)
                return
            self.pit.set_number_of_forwards(nack.name, 0)
            cur_fib_entry = self.fib.find_fib_entry(nack.name, cur_pit_entry.fib_entries_already_used, cur_pit_entry.faceids) #current entry
            self.pit.add_used_fib_entry(nack.name, cur_fib_entry) #add current entry to used list, modiefies pit entry in pit
            pit_entry = self.pit.find_pit_entry(nack.name) #read modified entry from pit
            fib_entry = self.fib.find_fib_entry(nack.name, pit_entry.fib_entries_already_used, pit_entry.faceids) #read new fib entry
            if fib_entry is None or fib_entry.faceid == [face_id]: #FIXME WHAT IS THE RIGHT CONDITION HERE?
                self.logger.info("Sending NACK to previous node(s)")
                re_add = False
                for i in range(0, len(pit_entry.faceids)):
                    if pit_entry.local_app[i] == True: #Go with NACK first only to app layer if it was requested
                        self.logger.info("Nack goes only to local first")
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
                self.logger.info("Try using next FIB path with FaceID: " + str(fib_entry.faceid))
                for fid in fib_entry.faceid:
                    if not self.pit.test_faceid_was_nacked(pit_entry.name, fid):
                        self.pit.increase_number_of_forwards(pit_entry.name)
                        to_lower.put([fid, pit_entry.interest])

    def ageing(self):
        """Ageing the data structs"""
        try:
            self.logger.debug("Ageing")
            #PIT ageing
            retransmits, removed_pit_entries = self.pit.ageing()
            for pit_entry in retransmits:
                fib_entry = self.fib.find_fib_entry(pit_entry.name, pit_entry.fib_entries_already_used, pit_entry.faceids)
                if not fib_entry:
                    continue
                for fid in fib_entry.faceid:
                    if not self.pit.test_faceid_was_nacked(pit_entry.name, fid):
                        self.queue_to_lower.put([fid, pit_entry.interest])
            for pit_entry in removed_pit_entries:
                if not pit_entry:
                    continue
            #CS ageing
            self.cs.ageing()
        except Exception as e:
            self.logger.warning("Exception during ageing: " + str(e))
            pass
        finally:
            t = threading.Timer(self._ageing_interval, self.ageing)
            t.setDaemon(True)
            t.start()
