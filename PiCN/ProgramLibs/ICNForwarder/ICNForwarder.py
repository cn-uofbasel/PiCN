"""A ICN Forwarder using PiCN"""

import multiprocessing

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.RoutingLayer import BasicRoutingLayer
from PiCN.Layers.RoutingLayer.RoutingInformationBase import TreeRoutingInformationBase
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer

from PiCN.Layers.ICNLayer.ContentStore.ContentStoreMemoryPrefix import ContentStoreMemoryPrefix
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt
from PiCN.Packets import Name


class ICNForwarder(object):
    """A ICN Forwarder using PiCN"""

    def __init__(self, port=9000, log_level=255, encoder: BasicEncoder=None, routing: bool=False, peers=None,
                 autoconfig: bool=False):
        # debug level
        logger = Logger("ICNForwarder", log_level)

        # packet encoder
        if encoder is None:
            self.encoder = SimpleStringEncoder
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder

        self._autoconfig = autoconfig

        # initialize layers
        self.linklayer = UDP4LinkLayer(port, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icnlayer = BasicICNLayer(log_level=log_level)

        # setup data structures
        manager = multiprocessing.Manager()
        self.data_structs = manager.dict()
        self.data_structs['cs'] = ContentStoreMemoryPrefix()
        self.data_structs['fib'] = ForwardingInformationBaseMemoryPrefix()
        self.data_structs['pit'] = PendingInterstTableMemoryExact()
        if routing:
            self.data_structs['rib'] = TreeRoutingInformationBase()

        self.icnlayer._data_structs = self.data_structs

        self.lstack: LayerStack = LayerStack([
            self.icnlayer,
            self.packetencodinglayer,
            self.linklayer
        ])

        if self._autoconfig:
            self.autoconfiglayer: AutoconfigServerLayer = AutoconfigServerLayer(linklayer=self.linklayer,
                                                                                data_structs=self.data_structs,
                                                                                address='127.0.0.1',
                                                                                bcaddr='127.255.255.255',
                                                                                registration_prefixes=
                                                                                [(Name('/testnetwork/repos'), True)],
                                                                                log_level=log_level)
            self.lstack.insert(self.autoconfiglayer, below_of=self.icnlayer)

        if routing:
            self.routinglayer = BasicRoutingLayer(self.linklayer, self.data_structs, peers=peers, log_level=log_level)
            self.lstack.insert(self.routinglayer, below_of=self.icnlayer)

        # mgmt
        self.mgmt = Mgmt(self.data_structs, self.linklayer, self.linklayer.get_port(), self.stop_forwarder,
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
