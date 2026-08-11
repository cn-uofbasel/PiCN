"""Shared encode/decode logic for PacketEncodingLayer (ADR-003 extract-core).

Does not touch queue objects -- returns ``List[Outbound]`` for wrappers to apply.
"""

from typing import List, Optional

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Logger import Logger
from PiCN.Processes.Outbound import Outbound


class PacketEncodingCore:
    """Pure packet encode/decode logic shared by sync and async wrappers."""

    def __init__(self, encoder: Optional[BasicEncoder] = None, logger: Optional[Logger] = None):
        self._encoder = encoder
        self.logger = logger if logger is not None else Logger("PktEncCore", 255)

    @property
    def encoder(self) -> Optional[BasicEncoder]:
        return self._encoder

    @encoder.setter
    def encoder(self, encoder: BasicEncoder) -> None:
        self._encoder = encoder

    def encode(self, data):
        self.logger.info("Encode packet")
        return self._encoder.encode(data)

    def decode(self, data):
        self.logger.info("Decode packet")
        return self._encoder.decode(data)

    def check_data(self, data):
        """check if data from queue match the requirements"""
        if len(data) != 2:
            self.logger.warning("PacketEncoding Layer expects queue elements to have size 2")
            return (None, None)
        if type(data[0]) != int:
            self.logger.warning("PacketEncoding Layer expects first element to be a faceid (int)")
            return (None, None)
        #TODO test if data[1] has type packet or bin data? howto?
        return data[0], data[1]

    def handle_from_higher(self, data) -> List[Outbound]:
        face_id, packet = self.check_data(data)
        if face_id == None or packet is None:
            return []
        self.logger.info("Packet from higher, Faceid: " + str(face_id) + ", Name: " + str(packet.name))
        encoded_packet = self.encode(packet)
        if encoded_packet is None:
            self.logger.info("Dropping Packet since None")
            return []
        return [Outbound("lower", [face_id, encoded_packet])]

    def handle_from_lower(self, data) -> List[Outbound]:
        face_id, packet = self.check_data(data)
        if face_id == None or packet == None:
            return []
        decoded_packet = self.decode(packet)
        if decoded_packet is None:
            self.logger.info("Dropping Packet since None")
            return []
        self.logger.info("Packet from lower, Faceid: " + str(face_id) + ", Name: " + str(decoded_packet.name))
        return [Outbound("higher", [face_id, decoded_packet])]
