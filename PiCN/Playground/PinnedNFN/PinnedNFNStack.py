"""Repository Stack"""

from PiCN.Playground.PinnedNFN import PinnedComputationLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, NdnTlvEncoder
from PiCN.Logger import Logger


class PinnedNFNStack(object):
    def __init__(self, port=9500, log_level=255, encoder: BasicEncoder = NdnTlvEncoder):
        # debug level
        logger = Logger("Repo", log_level)

        # packet encoder
        encoder.set_log_level(log_level)
        self.encoder = encoder

        # initialize layers
        self.link_layer = BasicLinkLayer(port, log_level=log_level)
        self.packet_encoding_layer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icn_layer = BasicICNLayer()
        self.pinned_computation_layer = PinnedComputationLayer()

        # setup data structures
        # TODO - handle datastructs

        # setup stack
        self.stack: LayerStack = LayerStack([
            self.pinned_computation_layer,
            self.icn_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

    def start_forwarder(self):
        self.stack.start_all()

    def stop_forwarder(self):
        self.stack.stop_all()
        self.stack.close_all()
