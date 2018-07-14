"""Storage Layer"""

import multiprocessing

from PiCN.Packets import Content, Interest, Packet, Nack
from PiCN.Processes import LayerProcess


class StorageLayer(LayerProcess):
    def __init__(self, log_level=255, http_port=8080):
        super().__init__(logger_name="StorageLayer", log_level=log_level)
        self.storage = None

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        if isinstance(data, Content):
            self.logger.info("Add to cache: " + data.name.to_string())
            self.storage.add_content_object(data)

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
        cache_entry = self.storage.find_content_object(interest.name)
        if cache_entry is not None:
            self.logger.info("Found in cache")
            to_lower.put([face_id, cache_entry.content])
            return
        else:
            self.logger.info("Not found in cache")
            return

    def ageing(self):
        pass  # data should not be removed from cache
