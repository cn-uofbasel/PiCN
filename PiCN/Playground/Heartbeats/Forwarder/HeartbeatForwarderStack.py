"""An extended ICN Forwarder"""

from typing import List

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Processes import PiCNSyncDataStructFactory

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, BaseInterface
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt
from PiCN.Routing import BasicRouting

from PiCN.Playground.Heartbeats.Layers.NetworkLayer import HeartbeatNetworkLayer
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import HeartbeatPacketEncodingLayer
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import ExtendedNdnTlvEncoder

class HeartbeatForwarderStack(object):
    """A Extended ICN Forwarder"""

    def __init__(self, port=9000, log_level=255, encoder: ExtendedNdnTlvEncoder=None, interfaces: List[BaseInterface] = None):
        # debug level
        logger = Logger("ICNForwarder", log_level)

        # packet encoder
        if encoder is None:
            self.encoder = ()
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder

        # setup data structures
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

        #default interface
        if interfaces is not None:
            self.interfaces = interfaces
            mgmt_port = port
        else:
            interfaces = [UDP4Interface(port)]
            mgmt_port = interfaces[0].get_port()

        # initialize layers
        self.link_layer = BasicLinkLayer(interfaces, face_id_table, log_level=log_level)
        self.packet_encoding_layer = HeartbeatPacketEncodingLayer(self.encoder, log_level=log_level) # TODO -- exchange this layer
        self.icn_layer = HeartbeatNetworkLayer(log_level=log_level)



        self.lstack: LayerStack = LayerStack([
            self.icn_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

        self.icn_layer.cs = cs
        self.icn_layer.fib = fib
        self.icn_layer.pit = pit

        # routing
        self.routing = BasicRouting(self.icn_layer.pit, None, log_level=log_level) #TODO NOT IMPLEMENTED YET

        # mgmt
        self.mgmt = Mgmt(cs, fib, pit, self.link_layer, mgmt_port, self.stop_forwarder,
                         log_level=log_level)

    def start_forwarder(self):
        # start processes
        self.lstack.start_all()
        self.icn_layer.ageing()
        self.mgmt.start_process()

    def stop_forwarder(self):
        #Stop processes
        self.mgmt.stop_process()
        self.lstack.stop_all()
        # close queues file descriptors
        self.lstack.close_all()
