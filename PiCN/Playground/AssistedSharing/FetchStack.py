"""Fetch Stack"""

from PiCN.LayerStack import LayerStack
from PiCN.Playground.AssistedSharing.FetchLayer import FetchLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder.NdnTlvEncoder import NdnTlvEncoder


class FetchStack(object):
    """Fetch Stack"""

    def __init__(self, ip: str, port: int, log_level=255):
        """
        Create stack of layers for fetch tool (UDP only)
        :param ip: IP address of entry node to network
        :param port: Port address of entry node to network
        :param log_level: Log level
        """
        # create encoder
        self.encoder = NdnTlvEncoder()

        # create layers
        self.link_layer = UDP4LinkLayer(0, log_level=log_level)
        self.packet_encoding_layer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.fetch_layer = FetchLayer(self.chunkifyer, log_level)

        self.layer_stack: LayerStack = LayerStack([
            self.fetch_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

        # setup face
        self.fid = self.link_layer.create_new_fid((ip, port), True)

        # create packet
        self.layer_stack.start_all()

    def stop_fetch(self):
        """
        Stop all layers
        :return: None
        """
        self.layer_stack.stop_all()
        self.layer_stack.close_all()
