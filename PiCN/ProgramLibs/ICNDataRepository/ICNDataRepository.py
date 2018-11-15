"""A ICN Repository using PiCN"""

from typing import Optional

import multiprocessing
from typing import List

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.RepositoryLayer import BasicRepositoryLayer
from PiCN.Layers.AutoconfigLayer import AutoconfigRepoLayer

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, BaseInterface
from PiCN.Processes.PiCNSyncDataStructFactory import PiCNSyncDataStructFactory
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Layers.RepositoryLayer.Repository import BaseRepository, SimpleFileSystemRepository, SimpleMemoryRepository
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList
from PiCN.Layers.ThunkLayer.BasicThunkLayer import BasicThunkLayer
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Logger import Logger
from PiCN.Packets import Name
from PiCN.Mgmt import Mgmt

# ----------------------------------------------------------------------

class ICNDataRepository(object):
    """A ICN Forwarder using PiCN"""

    def __init__(self, foldername: Optional[str], prefix: Name,
                 port=9000, log_level=255, encoder: BasicEncoder = None,
                 autoconfig: bool = False, autoconfig_routed: bool = False, interfaces: List[BaseInterface]=None,
                 use_thunks=False):
        """
        :param foldername: If None, use an in-memory repository. Else, use a file system repository.
        """

        logger = Logger("ICNRepo", log_level)
        logger.info("Start PiCN Data Repository")

        #packet encoder
        if encoder == None:
            self.encoder = SimpleStringEncoder(log_level = log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder
        #chunkifyer
        self.chunkifyer = SimpleContentChunkifyer()

        #repo
        manager = multiprocessing.Manager()

        if foldername is None:
            self.repo: BaseRepository = SimpleMemoryRepository(prefix, manager, logger)
        else:
            self.repo: BaseRepository = SimpleFileSystemRepository(foldername, prefix, manager, logger)

        #initialize layers
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        if use_thunks:
            synced_data_struct_factory.register("thunktable", ThunkList)
            synced_data_struct_factory.register("plantable", PlanTable)
        synced_data_struct_factory.create_manager()
        faceidtable = synced_data_struct_factory.manager.faceidtable()
        if use_thunks:
            self.parser = DefaultNFNParser()
            thunktable = synced_data_struct_factory.manager.thunktable()
            plantable = synced_data_struct_factory.manager.plantable(self.parser)

        if interfaces is not None:
            self.interfaces = interfaces
            mgmt_port = port
        else:
            interfaces = [UDP4Interface(port)]
            mgmt_port = interfaces[0].get_port()

        self.linklayer = BasicLinkLayer(interfaces, faceidtable, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.chunklayer = BasicChunkLayer(self.chunkifyer, log_level=log_level)
        self.repolayer = BasicRepositoryLayer(self.repo, log_level=log_level)

        if use_thunks:
            self.thunklayer = BasicThunkLayer(None, None, None, faceidtable, thunktable, plantable, self.parser, self.repo, log_level=log_level)
            logger.info("Using Thunks")

        if use_thunks:
            self.lstack: LayerStack = LayerStack([
                self.repolayer,
                self.chunklayer,
                self.thunklayer,
                self.packetencodinglayer,
                self.linklayer
            ])
        else:
            self.lstack: LayerStack = LayerStack([
                self.repolayer,
                self.chunklayer,
                self.packetencodinglayer,
                self.linklayer
            ])

        if autoconfig:
            self.autoconfiglayer = AutoconfigRepoLayer(name=prefix.string_components[-1],
                                                       addr='127.0.0.1',
                                                       linklayer=self.linklayer, repo=self.repo,
                                                       register_global=autoconfig_routed, log_level=log_level)
            self.lstack.insert(self.autoconfiglayer, below_of=self.chunklayer)


        # mgmt
        self.mgmt = Mgmt(None, None, None, self.linklayer, mgmt_port,
                         self.start_repo, repo_path=foldername,
                         repo_prfx=prefix, log_level=log_level)

    def start_repo(self):
        # start processes
        self.lstack.start_all()
        self.mgmt.start_process()

    def stop_repo(self):
        #Stop processes
        self.lstack.stop_all()
        self.lstack.close_all()
        self.mgmt.stop_process()

# eof
