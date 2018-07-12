"""Extended ICN Forwarding Layer (heartbeat)"""

import multiprocessing

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore, ContentStoreEntry
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, ForwardingInformationBaseEntry
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable, PendingInterestTableEntry
from PiCN.Packets import Name, Content, Interest, Packet, Nack, NackReason
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import Heartbeat
from PiCN.Layers.ICNLayer import BasicICNLayer


class HeartbeatNetworkLayer(BasicICNLayer):

    def __init__(self, cs: BaseContentStore=None, pit: BasePendingInterestTable=None,
                 fib: BaseForwardingInformationBase=None, log_level=255):
        super().__init__(log_level=log_level)
        # self.cs = cs
        # self.pit = pit
        # self.fib = fib
        # self._ageing_interval: int = 4
        # self._interest_to_app: bool = False

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass # this is the highest payer

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
        elif isinstance(packet, Heartbeat):
            self.handle_heartbeat(face_id, packet, to_lower, to_higher, False)

    def handle_heartbeat(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue,
                        to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Handling Heartbeat")
        #if to_higher is not None: #TODO check if app layer accepted the data, and change handling

        # cs_entry = self.cs.find_content_object(interest.name)
        # if cs_entry is not None:
        #     self.logger.info("Found in content store")
        #     to_lower.put([face_id, cs_entry.content])
        #     self.cs.update_timestamp(cs_entry)
        #     return
        # pit_entry = self.pit.find_pit_entry(interest.name)
        # if pit_entry is not None:
        #     self.logger.info("Found in PIT, appending")
        #     self.pit.update_timestamp(pit_entry)
        #     self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
        #     return
        # if self._interest_to_app is True and to_higher is not None: #App layer support
        #     self.logger.info("Sending to higher Layer")
        #     self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
        #     self.queue_to_higher.put([face_id, interest])
        #     return
        # new_face_id = self.fib.find_fib_entry(interest.name, None, [face_id])
        # if new_face_id is not None:
        #     self.logger.info("Found in FIB, forwarding")
        #     self.pit.add_pit_entry(interest.name, face_id, interest, local_app=from_local)
        #     #self.add_used_fib_entry_to_pit(interest.name, new_face_id) #disabled, should only be applied if nack is received.
        #     to_lower.put([new_face_id.faceid, interest])
        #     return
        # self.logger.info("No FIB entry, sending Nack")
        # nack = Nack(interest.name, NackReason.NO_ROUTE, interest=interest)
        # if from_local:
        #     to_higher.put([face_id, nack])
        # else:
        #     to_lower.put([face_id, nack])
