"""A ICN Forwarder using PiCN"""

from typing import List

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, BaseInterface
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Routing import BasicRouting


class ICNForwarder(object):
    """A ICN Forwarder using PiCN"""

    def __init__(self, port=9000, log_level=255, encoder: BasicEncoder = None, interfaces: List[BaseInterface] = None):
        # debug level
        logger = Logger("ICNForwarder", log_level)

        # packet encoder
        if encoder is None:
            self.encoder = SimpleStringEncoder()
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder

        # setup data structures
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        # default interface
        if interfaces is not None:
            self.interfaces = interfaces
            mgmt_port = port
        else:
            interfaces = [UDP4Interface(port)]
            mgmt_port = interfaces[0].get_port()

        # initialize layers
        self.linklayer = BasicLinkLayer(interfaces, faceidtable, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icnlayer = BasicICNLayer(log_level=log_level)

        self.lstack: LayerStack = LayerStack([
            self.icnlayer,
            self.packetencodinglayer,
            self.linklayer
        ])

        self.icnlayer.cs = cs
        self.icnlayer.fib = fib
        self.icnlayer.pit = pit

        # routing
        self.routing = BasicRouting(self.icnlayer.pit, None, log_level=log_level)  # TODO NOT IMPLEMENTED YET

        # mgmt
        self.mgmt = Mgmt(cs, fib, pit, self.linklayer, mgmt_port, self.stop_forwarder,
                         log_level=log_level)

    def start_forwarder(self):
        # start processes
        self.lstack.start_all()
        self.icnlayer.ageing()
        self.mgmt.start_process()

    def stop_forwarder(self):
        # Stop processes
        self.mgmt.stop_process()
        self.lstack.stop_all()
        # close queues file descriptors
        self.lstack.close_all()
