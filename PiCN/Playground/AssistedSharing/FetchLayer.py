"""Fetch Layer: fetch a high-level object"""

import multiprocessing
import mmap
import math
import hashlib

from PiCN.Layers.ICNLayer.ContentStore.ContentStoreMemoryExact import ContentStoreMemoryExact
from PiCN.Packets import Content, Interest, Packet, Nack, NackReason, Name
from PiCN.Processes import LayerProcess
from PiCN.Playground.AssistedSharing.SampleData import alice_index_schema, ac_wrapper_desc


class FetchLayer(LayerProcess):
    def __init__(self, log_level=255):
        super().__init__(logger_name="FetchLayer", log_level=log_level)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass  # this is the highest layer in the stack

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
            self.handle_interest(face_id, packet, to_lower)
        elif isinstance(packet, Content):
            self.logger.info("Received Data Packet, do nothing")
            return
        elif isinstance(packet, Nack):
            self.logger.info("Received NACK, do nothing")
            return
        else:
            self.logger.info("Received Unknown Packet, do nothing")
            return

    def handle_interest(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue):
        """
        Handle incoming interest
        :param face_id: ID of incoming face
        :param interest: Interest
        :param to_lower: Queue to lower layer
        :return: None
        """
        pass

    def ageing(self):
        pass  # data should not be removed from cache
