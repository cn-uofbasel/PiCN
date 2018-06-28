"""NFN Forwarder for PICN"""

import multiprocessing

from PiCN.LayerStack import LayerStack
from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.LinkLayer import BasicLinkLayer

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Routing import BasicRouting
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict

class NFNForwarder(object):
    """NFN Forwarder for PICN"""
    # TODO add chunking layer
    def __init__(self, port=9000, log_level=255, encoder: BasicEncoder=None):
        # debug level
        logger = Logger("NFNForwarder", log_level)
        logger.info("Start PiCN NFN Forwarder on port " + str(port))

        # packet encoder
        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder

       # setup data structures
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)
        synced_data_struct_factory.register("faceidtable", FaceIDDict)

        synced_data_struct_factory.register("computation_table", NFNComputationList)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        #setup chunkifier
        self.chunkifier = SimpleContentChunkifyer()

        # default interface
        interfaces = [UDP4Interface(port)]

        # initialize layers
        self.linklayer = BasicLinkLayer(interfaces, faceidtable, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icnlayer = BasicICNLayer(log_level=log_level)
        self.chunklayer = BasicChunkLayer(self.chunkifier, log_level=log_level)

        # setup nfn
        self.icnlayer._interest_to_app = True
        self.executors = {"PYTHON": NFNPythonExecutor()}
        self.parser = DefaultNFNParser()
        self.r2cclient = TimeoutR2CHandler()
        comp_table = synced_data_struct_factory.manager.computation_table(self.r2cclient, self.parser)
        self.nfnlayer = BasicNFNLayer(cs, fib, pit, comp_table, self.executors, self.parser, self.r2cclient, log_level=log_level)

        self.lstack: LayerStack = LayerStack([
            self.nfnlayer,
            self.chunklayer,
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
        self.mgmt = Mgmt(self.icnlayer.cs, self.icnlayer.fib, self.icnlayer.pit, self.linklayer,
                         self.linklayer.interfaces[0].get_port(), self.stop_forwarder,
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
