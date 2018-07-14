"""Pinned NFN Stack"""

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, NdnTlvEncoder
from PiCN.Logger import Logger
from PiCN.Playground.PinnedNFN import PinnedComputationLayer
from PiCN.Processes import PiCNSyncDataStructFactory


class PinnedNFNStack(object):
    def __init__(self, replica_id, port=9500, log_level=255, encoder: BasicEncoder = NdnTlvEncoder):
        # debug level
        logger = Logger("Repo", log_level)

        # packet encoder
        encoder.set_log_level(log_level)
        self.encoder = encoder

        # create datastruct
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)
        synced_data_struct_factory.register("face_id_table", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        face_id_table = synced_data_struct_factory.manager.face_id_table()

        # initialize layers
        self.link_layer = BasicLinkLayer([UDP4Interface(port)], face_id_table, log_level=log_level)
        self.packet_encoding_layer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icn_layer = BasicICNLayer(log_level=log_level)
        self.pinned_computation_layer = PinnedComputationLayer(replica_id, log_level=log_level)

        # tell icn_layer that there is a higher layer which might satisfy interests
        self.icn_layer._interest_to_app = True  # TODO -- decide here if it should be forwarded upwards or not
        # self.icn_layer._interest_to_app = lambda interest: interest.name.components[-1] == b"pNFN"

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
