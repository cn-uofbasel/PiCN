"""Pinned NFN Stack"""

from PiCN.Playground.PinnedNFN import PinnedComputationLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, NdnTlvEncoder
from PiCN.Processes import PiCNSyncDataStructFactory

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix

from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface
from PiCN.Logger import Logger


class PinnedNFNStack(object):
    def __init__(self, port=9500, log_level=255, encoder: BasicEncoder = NdnTlvEncoder):
        # debug level
        logger = Logger("Repo", log_level)

        # packet encoder
        encoder.set_log_level(log_level)
        self.encoder = encoder

        # create datastruct
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", BasePendingInterestTable)
        synced_data_struct_factory.register("face_id_table", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        face_id_table = synced_data_struct_factory.manager.face_id_table()

        # initialize layers
        self.link_layer = BasicLinkLayer(UDP4Interface(port), face_id_table, log_level=log_level)
        self.packet_encoding_layer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icn_layer = BasicICNLayer()
        self.pinned_computation_layer = PinnedComputationLayer()

        # setup stack
        self.stack: LayerStack = LayerStack([
            self.pinned_computation_layer,
            self.icn_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

        # set CS, FIB, PIT in forwarding layer
        self.icn_layer.cs = cs
        self.icn_layer.fib = fib
        self.icn_layer.pit = pit

    def start_forwarder(self):
        self.stack.start_all()

    def stop_forwarder(self):
        self.stack.stop_all()
        self.stack.close_all()
