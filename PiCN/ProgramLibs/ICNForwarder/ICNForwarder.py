"""A ICN Forwarder using PiCN"""

import multiprocessing

from typing import List

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.RoutingLayer import BasicRoutingLayer
from PiCN.Layers.RoutingLayer.RoutingInformationBase import TreeRoutingInformationBase
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer

from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer

from PiCN.Processes import PiCNSyncDataStructFactory

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo, BaseInterface
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt
from PiCN.Packets import Name


class ICNForwarder(object):
    """A ICN Forwarder using PiCN"""

    def __init__(self, port=9000, log_level=255, encoder: BasicEncoder=None, routing: bool=False, peers=None,
                 autoconfig: bool=False, interfaces: List[BaseInterface] = None, ageing_interval: int=3):
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
        synced_data_struct_factory.register("rib", TreeRoutingInformationBase)
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        if routing:
            rib = synced_data_struct_factory.manager.rib()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        #default interface
        if interfaces is not None:
            self.interfaces = interfaces
            mgmt_port = port
        else:
            interfaces = [UDP4Interface(port)]
            mgmt_port = interfaces[0].get_port()

        # initialize layers
        self.linklayer = BasicLinkLayer(interfaces, faceidtable, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icnlayer = BasicICNLayer(log_level=log_level, ageing_interval=ageing_interval)

        self.lstack: LayerStack = LayerStack([
            self.icnlayer,
            self.packetencodinglayer,
            self.linklayer
        ])

        if autoconfig:
            self.autoconfiglayer: AutoconfigServerLayer = AutoconfigServerLayer(linklayer=self.linklayer,
                                                                                address='127.0.0.1',
                                                                                registration_prefixes=
                                                                                [(Name('/testnetwork/repos'), True)],
                                                                                log_level=log_level)
            self.lstack.insert(self.autoconfiglayer, below_of=self.icnlayer)

        if routing:
            self.routinglayer = BasicRoutingLayer(self.linklayer, peers=peers, log_level=log_level)
            self.lstack.insert(self.routinglayer, below_of=self.icnlayer)

        self.icnlayer.cs = cs
        self.icnlayer.fib = fib
        self.icnlayer.pit = pit
        if autoconfig:
            self.autoconfiglayer.fib = fib
        if routing:
            self.routinglayer.rib = rib
            self.routinglayer.fib = fib

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
        self.lstack.stop_all()
        # close queues file descriptors
        if self.mgmt.process:
            self.mgmt.stop_process()
        self.lstack.close_all()
