"""Shared ICN forwarding logic (ADR-003 extract-core).

Returns ``List[Outbound]``; does not touch queue objects. Directions:
- ``\"lower\"`` / ``\"higher\"`` -- the handler's ``to_lower`` / ``to_higher`` args
- ``\"queue_lower\"`` / ``\"queue_higher\"`` -- the layer's instance queues
  (``self.queue_to_lower`` / ``self.queue_to_higher``), matching the observed
  sync code that sometimes puts on the instance queue rather than the
  handler argument (ADR-001).
"""

from typing import List, Optional

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Logger import Logger
from PiCN.Packets import Content, Interest, Packet, Nack, NackReason
from PiCN.Processes.Outbound import Outbound


class ICNLayerCore:
    """ICN forwarding plane logic shared by sync and async wrappers."""

    def __init__(self, cs: BaseContentStore = None, pit: BasePendingInterestTable = None,
                 fib: BaseForwardingInformationBase = None, rib: BaseRoutingInformationBase = None,
                 logger: Optional[Logger] = None, interest_to_app: bool = False):
        self.cs = cs
        self.pit = pit
        self.fib = fib
        self.rib = rib
        self.logger = logger if logger is not None else Logger("ICNCore", 255)
        self._interest_to_app = interest_to_app

    def handle_from_higher(self, data) -> List[Outbound]:
        high_level_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            return self.handle_interest_from_higher(high_level_id, packet)
        elif isinstance(packet, Content):
            return self.handle_content(high_level_id, packet, from_local=True, has_to_higher=True)
        elif isinstance(packet, Nack):
            return self.handle_nack(high_level_id, packet, from_local=True, has_to_higher=True)
        return []

    def handle_from_lower(self, data, has_to_higher: bool = True) -> List[Outbound]:
        if len(data) != 2:
            self.logger.warning("ICN Layer expects to receive [face id, packet] from lower layer")
            return []
        if type(data[0]) != int:
            self.logger.warning("ICN Layer expects to receive [face id, packet] from lower layer")
            return []
        if not isinstance(data[1], Packet):
            self.logger.warning("ICN Layer expects to receive [face id, packet] from lower layer")
            return []
        face_id = data[0]
        packet = data[1]
        self.logger.info("Received Packet from lower: " + str(face_id) + "; " + str(packet.name))
        if isinstance(packet, Interest):
            return self.handle_interest_from_lower(face_id, packet, from_local=False,
                                                   has_to_higher=has_to_higher)
        elif isinstance(packet, Content):
            return self.handle_content(face_id, packet, from_local=False, has_to_higher=has_to_higher)
        elif isinstance(packet, Nack):
            return self.handle_nack(face_id, packet, from_local=False, has_to_higher=has_to_higher)
        return []

    def handle_interest_from_higher(self, face_id: int, interest: Interest) -> List[Outbound]:
        out: List[Outbound] = []
        self.logger.info("Handling Interest (from higher): " + str(interest.name) + "; Face ID: " + str(face_id))
        cs_entry = self.cs.find_content_object(interest.name)
        if cs_entry is not None:
            # Observed: uses instance queue_to_higher, not the handler's to_higher.
            out.append(Outbound("queue_higher", [face_id, cs_entry.content]))
            return out
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
                        out.append(Outbound("lower", [fid, interest]))
                except Exception:
                    pass
        else:
            self.logger.info("No FIB entry, sending Nack: " + str(interest.name))
            nack = Nack(interest.name, NackReason.NO_ROUTE, interest=interest)
            if pit_entry is not None:
                for i in range(0, len(pit_entry.faceids)):
                    if pit_entry._local_app[i]:
                        out.append(Outbound("higher", [face_id, nack]))
                    else:
                        out.append(Outbound("lower", [pit_entry._faceids[i], nack]))
            else:
                out.append(Outbound("higher", [face_id, nack]))
        return out

    def handle_interest_from_lower(self, face_id: int, interest: Interest,
                                   from_local: bool = False, has_to_higher: bool = True) -> List[Outbound]:
        out: List[Outbound] = []
        self.logger.info("Handling Interest (from lower): " + str(interest.name) + "; Face ID: " + str(face_id))
        cs_entry = self.cs.find_content_object(interest.name)
        if cs_entry is not None:
            self.logger.info("Found in content store")
            out.append(Outbound("lower", [face_id, cs_entry.content]))
            self.cs.update_timestamp(cs_entry)
            return out
        pit_entry = self.pit.find_pit_entry(interest.name)
        if pit_entry is not None:
            self.logger.info("Found in PIT, appending")
            self.pit.update_timestamp(pit_entry)
            self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
            return out
        if self._interest_to_app is True and has_to_higher: #App layer support
            self.logger.info("Sending to higher Layer")
            self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
            out.append(Outbound("queue_higher", [face_id, interest]))
            return out
        new_face_id = self.fib.find_fib_entry(interest.name, None, [face_id])
        if new_face_id is not None:
            self.logger.info("Found in FIB, forwarding to Face: " + str(new_face_id.faceid))
            self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
            for fid in new_face_id.faceid:
                if not self.pit.test_faceid_was_nacked(interest.name, fid):
                    self.pit.increase_number_of_forwards(interest.name)
                    out.append(Outbound("lower", [fid, interest]))
            return out
        self.logger.info("No FIB entry, sending Nack")
        nack = Nack(interest.name, NackReason.NO_ROUTE, interest=interest)
        if from_local:
            out.append(Outbound("higher", [face_id, nack]))
        else:
            out.append(Outbound("lower", [face_id, nack]))
        return out

    def handle_content(self, face_id: int, content: Content, from_local: bool = False,
                       has_to_higher: bool = True) -> List[Outbound]:
        out: List[Outbound] = []
        self.logger.info("Handling Content " + str(content.name) + " " + str(content.content))
        pit_entry = self.pit.find_pit_entry(content.name)
        if pit_entry is None:
            self.logger.info("No PIT entry for content object available, dropping")
            return out
        for i in range(0, len(pit_entry.faceids)):
            if has_to_higher and pit_entry.local_app[i]:
                out.append(Outbound("higher", [face_id, content]))
            else:
                out.append(Outbound("lower", [pit_entry.faceids[i], content]))
        self.pit.remove_pit_entry(pit_entry.name)
        self.cs.add_content_object(content)
        return out

    def handle_nack(self, face_id: int, nack: Nack, from_local: bool = False,
                    has_to_higher: bool = True) -> List[Outbound]:
        out: List[Outbound] = []
        self.logger.info("Handling NACK: " + str(nack.name) + " Reason: " + str(nack.reason) + ", From FaceID: " +
                         str(face_id) + ", From Local: " + str(from_local))
        cur_pit_entry = self.pit.find_pit_entry(nack.name)
        if cur_pit_entry is None:
            self.logger.info("No PIT entry for NACK available, dropping")
            return out
        self.pit.add_nacked_faceid(nack.name, face_id)
        if cur_pit_entry.number_of_forwards > 1:
            self.logger.info("Ignoring Nack from FaceID " + str(face_id) + " for " + str(nack.name) + " since other faces (" + str(cur_pit_entry.number_of_forwards) + ") are still active")
            self.pit.decrease_number_of_forwards(nack.name)
            return out
        self.pit.set_number_of_forwards(nack.name, 0)
        cur_fib_entry = self.fib.find_fib_entry(nack.name, cur_pit_entry.fib_entries_already_used, cur_pit_entry.faceids)
        self.pit.add_used_fib_entry(nack.name, cur_fib_entry)
        pit_entry = self.pit.find_pit_entry(nack.name)
        fib_entry = self.fib.find_fib_entry(nack.name, pit_entry.fib_entries_already_used, pit_entry.faceids)
        if fib_entry is None or fib_entry.faceid == [face_id]:
            if self._interest_to_app and not from_local and 'THUNK' in str(nack.name):
                self.logger.info("Sending Thunk Nack to upper")
                out.append(Outbound("queue_higher", [face_id, nack]))
                return out
            self.logger.info("Sending NACK to previous node(s)")
            re_add = False
            for i in range(0, len(pit_entry.faceids)):
                if pit_entry.local_app[i] == True:
                    self.logger.info("Nack goes only to local first")
                    re_add = True
            self.pit.remove_pit_entry(pit_entry.name)
            indices_to_remove = []
            for i in range(0, len(pit_entry.faceids)):
                if has_to_higher and pit_entry.local_app[i]:
                    out.append(Outbound("higher", [face_id, nack]))
                    indices_to_remove.append(i)
                elif not re_add:
                    out.append(Outbound("lower", [pit_entry.faceids[i], nack]))
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
                    out.append(Outbound("lower", [fid, pit_entry.interest]))
        return out

    def ageing(self) -> List[Outbound]:
        """Age PIT/CS; return outbound retransmits and timeout Nacks. Does not schedule a timer."""
        out: List[Outbound] = []
        try:
            self.logger.debug("Ageing")
            retransmits, removed_pit_entries = self.pit.ageing()
            for pit_entry in retransmits:
                fib_entry = self.fib.find_fib_entry(pit_entry.name, pit_entry.fib_entries_already_used, pit_entry.faceids)
                if not fib_entry:
                    continue
                for fid in fib_entry.faceid:
                    if not self.pit.test_faceid_was_nacked(pit_entry.name, fid):
                        out.append(Outbound("queue_lower", [fid, pit_entry.interest]))
            for pit_entry in removed_pit_entries:
                if not pit_entry:
                    continue
                for fid, local in zip(pit_entry.faceids, pit_entry.local_app):
                    if local is True:
                        out.append(Outbound("queue_higher",
                                            [fid, Nack(pit_entry.name, NackReason.PIT_TIMEOUT, pit_entry.interest)]))
            self.cs.ageing()
        except Exception as e:
            self.logger.warning("Exception during ageing: " + str(e))
        return out
