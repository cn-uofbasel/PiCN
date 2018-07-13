"""Extended ICN Forwarding Layer (heartbeat)"""

import multiprocessing

from PiCN.Packets import Name, Content, Interest, Packet, Nack, NackReason
from PiCN.Playground.Heartbeats.Layers.PacketEncoding.Heartbeat import Heartbeat
from PiCN.Layers.ICNLayer import BasicICNLayer


class HeartbeatNetworkLayer(BasicICNLayer):
    def __init__(self, log_level=255, interest_to_app: bool = False):
        super().__init__(log_level=log_level)
        # self.cs = cs
        # self.pit = pit
        # self.fib = fib
        # self._ageing_interval: int = 4
        self._interest_to_app: bool = interest_to_app

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
            self.handle_heartbeat(packet)

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
        elif isinstance(packet, Heartbeat):
            self.handle_heartbeat(packet)

    def handle_heartbeat(self, heartbeat: Heartbeat):
        self.logger.info("Handling Heartbeat")

        # check if there is matching PIT entry
        pit_entry = self.pit.find_pit_entry(heartbeat.name)
        if pit_entry is not None:
            self.logger.info("Found PIT entry to update")
            self.pit.update_timestamp(pit_entry)
            # TODO -- forward heartbeat
            return
        else:
            self.logger.info("No PIT entry found")
