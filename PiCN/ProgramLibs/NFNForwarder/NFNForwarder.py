"""NFN Forwarder for PICN"""

import multiprocessing

from PiCN.LayerStack import LayerStack
from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.LinkLayer import UDP4LinkLayer

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt
from PiCN.Routing import BasicRouting

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

        # initialize layers
        self.linklayer = UDP4LinkLayer(port, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.icnlayer = BasicICNLayer(log_level=log_level)

        # setup data structures
        manager = multiprocessing.Manager()
        self.data_structs = manager.dict()
        self.data_structs['cs'] = ContentStoreMemoryExact()
        self.fib = ForwardingInformationBaseMemoryPrefix(manager)
        self.pit = PendingInterstTableMemoryExact(manager)

        self.icnlayer._data_structs = self.data_structs
        self.icnlayer.fib = self.fib
        self.icnlayer.pit = self.pit

        self.chunkifier = SimpleContentChunkifyer()

        # setup chunklayer
        self.chunklayer = BasicChunkLayer(self.chunkifier, log_level=log_level)

        # setup nfn
        self.icnlayer._interest_to_app = True
        self.executors = {"PYTHON": NFNPythonExecutor}
        self.nfnlayer = BasicNFNLayer(manager, self.icnlayer._data_structs, self.fib, self.pit, self.executors,
                                      log_level=log_level)

        self.lstack: LayerStack = LayerStack([
            self.nfnlayer,
            self.chunklayer,
            self.icnlayer,
            self.packetencodinglayer,
            self.linklayer
        ])

        # routing
        self.routing = BasicRouting(self.icnlayer.pit, None, log_level=log_level)  # TODO NOT IMPLEMENTED YET

        # mgmt
        self.mgmt = Mgmt(self.data_structs, self.fib, self.pit, self.linklayer, self.linklayer.get_port(), self.stop_forwarder,
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
