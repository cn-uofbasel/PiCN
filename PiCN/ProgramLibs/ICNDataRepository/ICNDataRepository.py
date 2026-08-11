"""A ICN Repository using PiCN"""

from typing import Optional, List, Union

import multiprocessing

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.Layers.ChunkLayer import BasicChunkLayer, AsyncBasicChunkLayer
from PiCN.Layers.PacketEncodingLayer import (
    BasicPacketEncodingLayer,
    AsyncBasicPacketEncodingLayer,
)
from PiCN.Layers.RepositoryLayer import (
    BasicRepositoryLayer,
    AsyncBasicRepositoryLayer,
)
from PiCN.Layers.AutoconfigLayer import AutoconfigRepoLayer, AsyncAutoconfigRepoLayer

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import BasicLinkLayer, AsyncBasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, BaseInterface
from PiCN.Processes.PiCNSyncDataStructFactory import PiCNSyncDataStructFactory
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Layers.RepositoryLayer.Repository import (
    BaseRepository,
    SimpleFileSystemRepository,
    SimpleMemoryRepository,
)
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList
from PiCN.Layers.ThunkLayer.BasicThunkLayer import BasicThunkLayer
from PiCN.Layers.ThunkLayer.AsyncBasicThunkLayer import AsyncBasicThunkLayer
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Logger import Logger
from PiCN.Packets import Name
from PiCN.Mgmt import Mgmt, AsyncMgmt
from PiCN.ProgramLibs.runtime import Runtime
from PiCN.ProgramLibs.plain_manager import PlainRepoManager


class ICNDataRepository(object):
    """A ICN Repository using PiCN

    :param runtime: ``Runtime.SYNC`` (default) or ``Runtime.ASYNC``.
    """

    def __init__(
        self,
        foldername: Optional[str],
        prefix: Name,
        port=9000,
        log_level=255,
        encoder: BasicEncoder = None,
        autoconfig: bool = False,
        autoconfig_routed: bool = False,
        interfaces: List[BaseInterface] = None,
        use_thunks=False,
        runtime: Union[Runtime, str] = Runtime.SYNC,
    ):
        if isinstance(runtime, str):
            runtime = Runtime(runtime)
        self.runtime = runtime

        logger = Logger("ICNRepo", log_level)
        logger.info("Start PiCN Data Repository")

        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder
        self.chunkifyer = SimpleContentChunkifyer()

        if runtime is Runtime.ASYNC:
            manager = PlainRepoManager()
        else:
            manager = multiprocessing.Manager()

        if foldername is None:
            self.repo: BaseRepository = SimpleMemoryRepository(
                prefix, manager, logger)
        else:
            self.repo: BaseRepository = SimpleFileSystemRepository(
                foldername, prefix, manager, logger)

        if runtime is Runtime.ASYNC:
            faceidtable = FaceIDDict()
            if use_thunks:
                self.parser = DefaultNFNParser()
                thunktable = ThunkList()
                plantable = PlanTable(self.parser)
        else:
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
                plantable = synced_data_struct_factory.manager.plantable(
                    self.parser)

        if interfaces is not None:
            self.interfaces = interfaces
            mgmt_port = port
        else:
            interfaces = [UDP4Interface(port)]
            self.interfaces = interfaces
            mgmt_port = interfaces[0].get_port()

        if runtime is Runtime.ASYNC:
            self.linklayer = AsyncBasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = AsyncBasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.chunklayer = AsyncBasicChunkLayer(
                self.chunkifyer, log_level=log_level)
            self.repolayer = AsyncBasicRepositoryLayer(
                self.repo, log_level=log_level)
            layers = [self.repolayer, self.chunklayer]
            if use_thunks:
                self.thunklayer = AsyncBasicThunkLayer(
                    None, None, None, faceidtable, thunktable, plantable,
                    self.parser, self.repo, log_level=log_level)
                layers.append(self.thunklayer)
            layers.extend([self.packetencodinglayer, self.linklayer])
            self.lstack = AsyncLayerStack(layers)
            if autoconfig:
                self.autoconfiglayer = AsyncAutoconfigRepoLayer(
                    name=prefix.string_components[-1],
                    addr="127.0.0.1",
                    linklayer=self.linklayer,
                    repo=self.repo,
                    register_global=autoconfig_routed,
                    log_level=log_level,
                )
                self.lstack.insert(self.autoconfiglayer, below_of=self.chunklayer)
            self.mgmt = AsyncMgmt(
                None, None, None, self.linklayer, mgmt_port,
                self.start_repo_async, repo_path=foldername,
                repo_prfx=prefix, log_level=log_level)
        else:
            self.linklayer = BasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = BasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.chunklayer = BasicChunkLayer(
                self.chunkifyer, log_level=log_level)
            self.repolayer = BasicRepositoryLayer(
                self.repo, log_level=log_level)
            if use_thunks:
                self.thunklayer = BasicThunkLayer(
                    None, None, None, faceidtable, thunktable, plantable,
                    self.parser, self.repo, log_level=log_level)
                self.lstack: LayerStack = LayerStack([
                    self.repolayer,
                    self.chunklayer,
                    self.thunklayer,
                    self.packetencodinglayer,
                    self.linklayer,
                ])
            else:
                self.lstack: LayerStack = LayerStack([
                    self.repolayer,
                    self.chunklayer,
                    self.packetencodinglayer,
                    self.linklayer,
                ])
            if autoconfig:
                self.autoconfiglayer = AutoconfigRepoLayer(
                    name=prefix.string_components[-1],
                    addr="127.0.0.1",
                    linklayer=self.linklayer,
                    repo=self.repo,
                    register_global=autoconfig_routed,
                    log_level=log_level,
                )
                self.lstack.insert(self.autoconfiglayer, below_of=self.chunklayer)
            self.mgmt = Mgmt(
                None, None, None, self.linklayer, mgmt_port,
                self.start_repo, repo_path=foldername,
                repo_prfx=prefix, log_level=log_level)

    def start_repo(self):
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "ICNDataRepository was built with runtime=async; "
                "use await start_repo_async()"
            )
        self.lstack.start_all()
        self.mgmt.start_process()

    def stop_repo(self):
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "ICNDataRepository was built with runtime=async; "
                "use await stop_repo_async()"
            )
        self.lstack.stop_all()
        self.lstack.close_all()
        self.mgmt.stop_process()

    async def start_repo_async(self) -> None:
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "ICNDataRepository was built with runtime=sync; use start_repo()"
            )
        self.lstack.start_all()
        await self.mgmt.start()

    async def stop_repo_async(self) -> None:
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "ICNDataRepository was built with runtime=sync; use stop_repo()"
            )
        await self.mgmt.stop()
        await self.lstack.stop_all()
