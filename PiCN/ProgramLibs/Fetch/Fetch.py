"""Fetch Tool for PiCN"""

from typing import List, Optional, Union

from PiCN.LayerStack import LayerStack
from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.Layers.AutoconfigLayer import AutoconfigClientLayer, AsyncAutoconfigClientLayer
from PiCN.Layers.ChunkLayer import BasicChunkLayer, AsyncBasicChunkLayer
from PiCN.Layers.PacketEncodingLayer import (
    BasicPacketEncodingLayer,
    AsyncBasicPacketEncodingLayer,
)
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import BasicLinkLayer, AsyncBasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Processes.PiCNSyncDataStructFactory import PiCNSyncDataStructFactory
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Content, Name, Interest, Nack
from PiCN.Layers.TimeoutPreventionLayer import (
    BasicTimeoutPreventionLayer,
    AsyncBasicTimeoutPreventionLayer,
    TimeoutPreventionMessageDict,
)
from PiCN.ProgramLibs.runtime import Runtime


class Fetch(object):
    """Fetch Tool for PiCN

    :param runtime: ``Runtime.SYNC`` (default) starts the stack in ``__init__``
        as today; ``Runtime.ASYNC`` defers start to ``await start_fetch_async()``.
    """

    def __init__(
        self,
        ip: str,
        port: int,
        log_level=255,
        encoder: BasicEncoder = None,
        autoconfig: bool = False,
        interfaces=None,
        runtime: Union[Runtime, str] = Runtime.SYNC,
    ):
        if isinstance(runtime, str):
            runtime = Runtime(runtime)
        self.runtime = runtime

        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder
        self.chunkifyer = SimpleContentChunkifyer()
        self.autoconfig = autoconfig

        if interfaces is None:
            interfaces = [UDP4Interface(0)]
        self.interfaces = interfaces

        if runtime is Runtime.ASYNC:
            faceidtable = FaceIDDict()
            timeoutprevention_dict = TimeoutPreventionMessageDict()
            self.linklayer = AsyncBasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = AsyncBasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.chunklayer = AsyncBasicChunkLayer(
                self.chunkifyer, log_level=log_level)
            self.timeoutpreventionlayer = AsyncBasicTimeoutPreventionLayer(
                timeoutprevention_dict, None, log_level=log_level)
            self.lstack = AsyncLayerStack([
                self.chunklayer,
                self.timeoutpreventionlayer,
                self.packetencodinglayer,
                self.linklayer,
            ])
            if autoconfig:
                self.autoconfiglayer = AsyncAutoconfigClientLayer(self.linklayer)
                self.lstack.insert(
                    self.autoconfiglayer, on_top_of=self.packetencodinglayer)
            # Do NOT start_all() or ageing() here -- no event loop yet (Task 5.3).
        else:
            synced_data_struct_factory = PiCNSyncDataStructFactory()
            synced_data_struct_factory.register("faceidtable", FaceIDDict)
            synced_data_struct_factory.register(
                "timeoutprevention_dict", TimeoutPreventionMessageDict)
            synced_data_struct_factory.create_manager()
            faceidtable = synced_data_struct_factory.manager.faceidtable()
            timeoutprevention_dict = (
                synced_data_struct_factory.manager.timeoutprevention_dict())

            self.linklayer = BasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = BasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.chunklayer = BasicChunkLayer(
                self.chunkifyer, log_level=log_level)
            self.timeoutpreventionlayer = BasicTimeoutPreventionLayer(
                timeoutprevention_dict, None, log_level=log_level)
            self.lstack: LayerStack = LayerStack([
                self.chunklayer,
                self.timeoutpreventionlayer,
                self.packetencodinglayer,
                self.linklayer,
            ])
            self.timeoutpreventionlayer.ageing()
            if autoconfig:
                self.autoconfiglayer: AutoconfigClientLayer = AutoconfigClientLayer(
                    self.linklayer)
                self.lstack.insert(
                    self.autoconfiglayer, on_top_of=self.packetencodinglayer)
            self.lstack.start_all()

        if port is None:
            self.fid = self.linklayer.faceidtable.get_or_create_faceid(
                AddressInfo(ip, 0))
        else:
            self.fid = self.linklayer.faceidtable.get_or_create_faceid(
                AddressInfo((ip, port), 0))

    def fetch_data(self, name: Name, timeout=4.0) -> str:
        """Fetch data from the server (sync runtime)."""
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "Fetch was built with runtime=async; use await fetch_data_async()"
            )
        interest: Interest = Interest(name)
        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, interest])
        else:
            self.lstack.queue_from_higher.put([self.fid, interest])

        if timeout == 0:
            packet = self.lstack.queue_to_higher.get()[1]
        else:
            packet = self.lstack.queue_to_higher.get(timeout=timeout)[1]
        if isinstance(packet, Content):
            return packet.content
        if isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)
        return None

    async def start_fetch_async(self) -> None:
        """Start the async Fetch stack. Ageing starts from layer.start()."""
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "Fetch was built with runtime=sync; stack already started in __init__"
            )
        self.lstack.start_all()

    async def stop_fetch_async(self) -> None:
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "Fetch was built with runtime=sync; use stop_fetch()"
            )
        await self.lstack.stop_all()

    async def fetch_data_async(self, name: Name, timeout=4.0) -> Optional[str]:
        """Fetch data under the async runtime."""
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "Fetch was built with runtime=sync; use fetch_data()"
            )
        import asyncio
        interest: Interest = Interest(name)
        if self.autoconfig:
            await self.lstack.queue_from_higher.put([None, interest])
        else:
            await self.lstack.queue_from_higher.put([self.fid, interest])

        if timeout == 0:
            packet = (await self.lstack.queue_to_higher.get())[1]
        else:
            packet = (await asyncio.wait_for(
                self.lstack.queue_to_higher.get(), timeout=timeout))[1]
        if isinstance(packet, Content):
            return packet.content
        if isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)
        return None

    def stop_fetch(self):
        """Close everything (sync runtime)."""
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "Fetch was built with runtime=async; use await stop_fetch_async()"
            )
        self.lstack.stop_all()
        self.lstack.close_all()
