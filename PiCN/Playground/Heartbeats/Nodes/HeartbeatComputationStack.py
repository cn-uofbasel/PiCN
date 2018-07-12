"""Heartbeat NFN Stack"""

from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import ExtendedNdnTlvEncoder
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import HeartbeatPacketEncodingLayer
from PiCN.Playground.Heartbeats.Layers.ComputationLayer import HeartbeatComputationLayer
from PiCN.Playground.Heartbeats.Layers.NetworkLayer import HeartbeatNetworkLayer

from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix

from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface
from PiCN.Logger import Logger


class HeartbeatNFNStack(object):
    def __init__(self, replica_id, port=9500, log_level=255, encoder: ExtendedNdnTlvEncoder = ExtendedNdnTlvEncoder):
        # debug level
        logger = Logger("Server", log_level)

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
        self.packet_encoding_layer = HeartbeatPacketEncodingLayer(self.encoder, log_level=log_level)
        self.heartbeat_network_layer = HeartbeatNetworkLayer(log_level=log_level, interest_to_app=True)
        self.heartbeat_computation_layer = HeartbeatComputationLayer(log_level=log_level)

        # setup stack
        self.stack: LayerStack = LayerStack([
            self.heartbeat_computation_layer,
            self.heartbeat_network_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

        # set CS, FIB, PIT in forwarding layer
        self.heartbeat_network_layer.cs = cs
        self.heartbeat_network_layer.fib = fib
        self.heartbeat_network_layer.pit = pit

    def start_forwarder(self):
        self.stack.start_all()

    def stop_forwarder(self):
        self.stack.stop_all()
        self.stack.close_all()
