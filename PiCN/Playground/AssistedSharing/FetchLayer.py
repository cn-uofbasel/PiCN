"""Fetch Layer: fetch a high-level object"""

import multiprocessing

from PiCN.Packets import Content, Interest, Packet, Nack, Name
from PiCN.Processes import LayerProcess
from PiCN.Playground.AssistedSharing.WrapperDescription import WrapperDescription


class FetchLayer(LayerProcess):
    def __init__(self, log_level=255):
        super().__init__(logger_name="FetchLayer", log_level=log_level)
        self.high_level_name = None
        self.wrapper_description = None

    def trigger_fetching(self, high_level_name):
        """
        Trigger fetching of high level object
        :param high_level_name: Name of high level object
        :return: None
        """
        assert(self.high_level_name is None)
        # TODO -- set self.high_level_name
        # TODO -- send interest for high_level_name

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
            self.logger.info("Received Interest Packet, do nothing")
        elif isinstance(packet, Content):
            self.logger.info("Received Data Packet: " + packet.name)
            self.handle_content(packet, face_id, to_lower)
            return
        elif isinstance(packet, Nack):
            self.logger.info("Received NACK, do nothing")
            return
        else:
            self.logger.info("Received Unknown Packet, do nothing")
            return

    def handle_content(self, content: Content, face_id: int, to_lower: multiprocessing.Queue):
        """
        Handle received content object
        :param content: Received data packet
        :param face_id: Incoming face id
        :param to_lower: Queue to lower layer
        :return: None
        """
        if self.wrapper_description is None:
            if content.name is self.high_level_name:
                self.wrapper_description = WrapperDescription(content.content)
                self.do_encapsulation()
            else:
                self.logger.info("Received data but wrapper description not ready. Skip.")
                return
        else:
            pass # todo -- hand over to unwrapping procedure

    def do_encapsulation(self):
        """
        Start encapsulation (self.wrapper_description must be initialized)
        :return: None
        """
        pass # TODO

    def ageing(self):
        pass  # data should not be removed from cache
