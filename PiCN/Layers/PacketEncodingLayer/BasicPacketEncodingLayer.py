""" De- and Encoding Layer, using a predefined Encoder """

import multiprocessing
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Layers.PacketEncodingLayer.PacketEncodingCore import PacketEncodingCore
from PiCN.Processes import LayerProcess


class BasicPacketEncodingLayer(LayerProcess):
    """ De- and Encoding Layer, using a predefined Encoder

    Thin sync wrapper around :class:`PacketEncodingCore` (ADR-003 extract-core).
    """

    def __init__(self, encoder: BasicEncoder=None, log_level=255):
        LayerProcess.__init__(self, logger_name="PktEncLayer", log_level=log_level)
        self._core = PacketEncodingCore(encoder=encoder, logger=self.logger)

    @property
    def encoder(self):
        return self._core.encoder

    @encoder.setter
    def encoder(self, encoder):
        self._core.encoder = encoder

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_higher(data):
            if out.direction == "lower":
                to_lower.put(out.item)
            else:
                to_higher.put(out.item)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_lower(data):
            if out.direction == "lower":
                to_lower.put(out.item)
            else:
                to_higher.put(out.item)

    def encode(self, data):
        return self._core.encode(data)

    def decode(self, data):
        return self._core.decode(data)

    def check_data(self, data):
        """check if data from queue match the requirements"""
        return self._core.check_data(data)
