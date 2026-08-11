"""A ICN Forwarder using PiCN"""

from typing import List, Optional, Union

from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer, AsyncBasicICNLayer
from PiCN.Layers.RoutingLayer import BasicRoutingLayer, AsyncBasicRoutingLayer
from PiCN.Layers.PacketEncodingLayer import (
    BasicPacketEncodingLayer,
    AsyncBasicPacketEncodingLayer,
)
from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer, AsyncAutoconfigServerLayer
from PiCN.Layers.LinkLayer import BasicLinkLayer, AsyncBasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, BaseInterface
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt, AsyncMgmt
from PiCN.Packets import Name
from PiCN.ProgramLibs.runtime import Runtime, make_forwarding_tables


class ICNForwarder(object):
    """A ICN Forwarder using PiCN

    :param runtime: ``Runtime.SYNC`` (default) keeps today's multiprocessing
        stack; ``Runtime.ASYNC`` builds an in-process ``AsyncLayerStack``.
    """

    def __init__(
        self,
        port=9000,
        log_level=255,
        encoder: BasicEncoder = None,
        routing: bool = False,
        peers=None,
        autoconfig: bool = False,
        interfaces: List[BaseInterface] = None,
        ageing_interval: int = 3,
        runtime: Union[Runtime, str] = Runtime.SYNC,
    ):
        if isinstance(runtime, str):
            runtime = Runtime(runtime)
        self.runtime = runtime
        self._log_level = log_level
        self._ageing_interval = ageing_interval
        self._routing = routing
        self._autoconfig = autoconfig

        logger = Logger("ICNForwarder", log_level)

        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level=log_level)
            self.encoder = encoder

        tables = make_forwarding_tables(runtime, routing=routing)
        cs, fib, pit, faceidtable, rib = tables

        if interfaces is not None:
            self.interfaces = interfaces
            mgmt_port = port
        else:
            interfaces = [UDP4Interface(port)]
            self.interfaces = interfaces
            mgmt_port = interfaces[0].get_port()
        self._mgmt_port = mgmt_port

        if runtime is Runtime.ASYNC:
            self.linklayer = AsyncBasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = AsyncBasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.icnlayer = AsyncBasicICNLayer(
                log_level=log_level, ageing_interval=ageing_interval)
            self.lstack = AsyncLayerStack([
                self.icnlayer,
                self.packetencodinglayer,
                self.linklayer,
            ])
            if autoconfig:
                self.autoconfiglayer = AsyncAutoconfigServerLayer(
                    linklayer=self.linklayer,
                    address="127.0.0.1",
                    registration_prefixes=[(Name("/testnetwork/repos"), True)],
                    log_level=log_level,
                )
                self.lstack.insert(self.autoconfiglayer, below_of=self.icnlayer)
            if routing:
                self.routinglayer = AsyncBasicRoutingLayer(
                    self.linklayer, peers=peers, log_level=log_level)
                self.lstack.insert(self.routinglayer, below_of=self.icnlayer)
        else:
            self.linklayer = BasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = BasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.icnlayer = BasicICNLayer(
                log_level=log_level, ageing_interval=ageing_interval)
            self.lstack: LayerStack = LayerStack([
                self.icnlayer,
                self.packetencodinglayer,
                self.linklayer,
            ])
            if autoconfig:
                self.autoconfiglayer: AutoconfigServerLayer = AutoconfigServerLayer(
                    linklayer=self.linklayer,
                    address="127.0.0.1",
                    registration_prefixes=[(Name("/testnetwork/repos"), True)],
                    log_level=log_level,
                )
                self.lstack.insert(self.autoconfiglayer, below_of=self.icnlayer)
            if routing:
                self.routinglayer = BasicRoutingLayer(
                    self.linklayer, peers=peers, log_level=log_level)
                self.lstack.insert(self.routinglayer, below_of=self.icnlayer)

        self.icnlayer.cs = cs
        self.icnlayer.fib = fib
        self.icnlayer.pit = pit
        if autoconfig:
            self.autoconfiglayer.fib = fib
        if routing:
            self.routinglayer.rib = rib
            self.routinglayer.fib = fib

        if runtime is Runtime.ASYNC:
            self.mgmt = AsyncMgmt(
                cs, fib, pit, self.linklayer, mgmt_port,
                self.stop_forwarder_async, log_level=log_level)
        else:
            self.mgmt = Mgmt(
                cs, fib, pit, self.linklayer, mgmt_port, self.stop_forwarder,
                log_level=log_level)

    def start_forwarder(self):
        """Start the sync (multiprocessing) forwarder."""
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "ICNForwarder was built with runtime=async; "
                "use await start_forwarder_async()"
            )
        self.lstack.start_all()
        self.icnlayer.ageing()
        self.mgmt.start_process()

    def stop_forwarder(self):
        """Stop the sync (multiprocessing) forwarder."""
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "ICNForwarder was built with runtime=async; "
                "use await stop_forwarder_async()"
            )
        self.lstack.stop_all()
        if self.mgmt.process:
            self.mgmt.stop_process()
        self.lstack.close_all()

    async def start_forwarder_async(self) -> None:
        """Start the async forwarder (AsyncLayerStack + AsyncMgmt)."""
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "ICNForwarder was built with runtime=sync; "
                "use start_forwarder()"
            )
        self.lstack.start_all()
        # Ageing starts from AsyncBasicICNLayer.start() -- do not call ageing().
        await self.mgmt.start()

    async def stop_forwarder_async(self) -> None:
        """Stop AsyncMgmt then the layer stack (ADR-006 / ADR-009)."""
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "ICNForwarder was built with runtime=sync; "
                "use stop_forwarder()"
            )
        await self.mgmt.stop()
        await self.lstack.stop_all()
