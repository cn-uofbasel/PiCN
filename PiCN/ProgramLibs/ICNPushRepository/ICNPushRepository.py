"""A Push Repository using PiCN"""

from typing import Union

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.Layers.RepositoryLayer import PushRepositoryLayer, AsyncPushRepositoryLayer
from PiCN.Layers.PacketEncodingLayer import (
    BasicPacketEncodingLayer,
    AsyncBasicPacketEncodingLayer,
)
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Layers.ICNLayer.ContentStore import ContentStorePersistentExact
from PiCN.Layers.LinkLayer import BasicLinkLayer, AsyncBasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt, AsyncMgmt
from PiCN.ProgramLibs.runtime import Runtime


class ICNPushRepository(object):
    """A Push Repository using PiCN

    :param runtime: ``Runtime.SYNC`` (default) or ``Runtime.ASYNC``.
    """

    def __init__(
        self,
        database_path,
        port=9000,
        log_level=255,
        encoder: BasicEncoder = None,
        flush_database=False,
        runtime: Union[Runtime, str] = Runtime.SYNC,
    ):
        if isinstance(runtime, str):
            runtime = Runtime(runtime)
        self.runtime = runtime

        logger = Logger("PushRepo", log_level)

        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level=log_level)
            self.encoder = encoder

        if runtime is Runtime.ASYNC:
            cs = ContentStorePersistentExact(
                db_path=database_path + "/pushrepo.db")
            if flush_database:
                cs.delete_all()
            faceidtable = FaceIDDict()
        else:
            synced_data_struct_factory = PiCNSyncDataStructFactory()
            synced_data_struct_factory.register(
                "cs", ContentStorePersistentExact)
            synced_data_struct_factory.register("faceidtable", FaceIDDict)
            synced_data_struct_factory.create_manager()
            cs = synced_data_struct_factory.manager.cs(
                db_path=database_path + "/pushrepo.db")
            if flush_database:
                cs.delete_all()
            faceidtable = synced_data_struct_factory.manager.faceidtable()

        interfaces = [UDP4Interface(port)]
        self.interfaces = interfaces
        mgmt_port = interfaces[0].get_port()

        if runtime is Runtime.ASYNC:
            self.linklayer = AsyncBasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = AsyncBasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.repolayer = AsyncPushRepositoryLayer(log_level=log_level)
            self.lstack = AsyncLayerStack([
                self.repolayer,
                self.packetencodinglayer,
                self.linklayer,
            ])
            self.repolayer.cs = cs
            self.mgmt = AsyncMgmt(
                cs, None, None, self.linklayer, mgmt_port,
                self.stop_forwarder_async, log_level=log_level)
        else:
            self.linklayer = BasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = BasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.repolayer = PushRepositoryLayer(log_level=log_level)
            self.lstack: LayerStack = LayerStack([
                self.repolayer,
                self.packetencodinglayer,
                self.linklayer,
            ])
            self.repolayer.cs = cs
            self.mgmt = Mgmt(
                cs, None, None, self.linklayer, mgmt_port, self.stop_forwarder,
                log_level=log_level)

    def start_forwarder(self):
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "ICNPushRepository was built with runtime=async; "
                "use await start_forwarder_async()"
            )
        self.lstack.start_all()
        self.mgmt.start_process()

    def stop_forwarder(self):
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "ICNPushRepository was built with runtime=async; "
                "use await stop_forwarder_async()"
            )
        self.lstack.stop_all()
        if self.mgmt.process:
            self.mgmt.stop_process()
        self.lstack.close_all()

    async def start_forwarder_async(self) -> None:
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "ICNPushRepository was built with runtime=sync; "
                "use start_forwarder()"
            )
        self.lstack.start_all()
        await self.mgmt.start()

    async def stop_forwarder_async(self) -> None:
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "ICNPushRepository was built with runtime=sync; "
                "use stop_forwarder()"
            )
        await self.mgmt.stop()
        await self.lstack.stop_all()
