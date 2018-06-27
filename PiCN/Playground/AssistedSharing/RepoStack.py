"""Publisher Stack"""

import multiprocessing

from PiCN.Playground.AssistedSharing import RepoLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.LayerStack.LayerStack import LayerStack

from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, NdnTlvEncoder
from PiCN.Logger import Logger


class RepoStack(object):
    def __init__(self, port=8500, log_level=255, encoder: BasicEncoder = NdnTlvEncoder):
        # debug level
        logger = Logger("Publisher", log_level)

        # packet encoder
        encoder.set_log_level(log_level)
        self.encoder = encoder

        #create datastruct
        synced_data_struct_factory1 = PiCNSyncDataStructFactory()
        synced_data_struct_factory1.register("faceidtable", FaceIDDict)
        synced_data_struct_factory1.create_manager()
        faceidtable = synced_data_struct_factory1.manager.faceidtable()

        # initialize layers
        self.link_layer = BasicLinkLayer(UDP4Interface(), faceidtable, log_level=log_level)
        self.packet_encoding_layer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.repo_layer = RepoLayer(log_level=log_level)

        self.stack: LayerStack = LayerStack([
            self.repo_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

    def start_forwarder(self):
        self.stack.start_all()
        self.repo_layer.ageing()

    def stop_forwarder(self):
        self.stack.stop_all()
        self.stack.close_all()
