"""Repository Layer"""

import multiprocessing

from PiCN.Layers.ICNLayer.ContentStore.ContentStoreMemoryPrefix import ContentStoreMemoryPrefix
from PiCN.Packets import Content, Interest, Packet, Nack, NackReason
from PiCN.Processes import LayerProcess
from PiCN.Playground.AssistedSharing.SampleData import alice_index_schema


class RepoLayer(LayerProcess):

    def __init__(self, log_level=255, manager: multiprocessing.Manager=None):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        if manager is None:
            manager = multiprocessing.Manager()
        self._data_structs = manager.dict()
        cs = ContentStoreMemoryPrefix()
        cs.add_content_object(Content("/alice/schema.index", alice_index_schema))
        self._data_structs['cs'] = cs


    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass


    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        if len(data) != 2:
            self.logger.info("ICN Layer expects to receive [face id, packet] from lower layer")
            return
        if type(data[0]) != int:
            self.logger.info("ICN Layer expects to receive [face id, packet] from lower layer")
            return
        if not isinstance(data[1], Packet):
            self.logger.info("ICN Layer expects to receive [face id, packet] from lower layer")
            return

        face_id = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            self.handle_interest(face_id, packet, to_lower, to_higher, False)
        elif isinstance(packet, Content):
            self.logger.info("Received Data Packet, do nothing")
            return
        elif isinstance(packet, Nack):
            self.logger.info("Received NACK, do nothing")
            return
        else:
            self.logger.info("Received Unknown Packet, do nothing")
            return


    def handle_interest(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, from_local: bool = False):
        self.logger.info("Received Interest for " + interest.name.to_string())
        cs_entry = self._data_structs['cs'].find_content_object(interest.name)
        if cs_entry is not None:
            self.logger.info("Found in database")
            to_lower.put([face_id, cs_entry.content])
            return
        else:
            self.logger.info("Not found in database")
            nack = Nack(interest.name, NackReason.NO_CONTENT, interest=interest)
            to_higher.put([face_id, nack])


    def ageing(self):
            pass
