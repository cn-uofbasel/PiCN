"""Async autoconfig server layer wrapper (ADR-003)."""

from typing import List, Tuple

from PiCN.Layers.AutoconfigLayer.AutoconfigLayerCore import AutoconfigServerCore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Packets import Name, Packet
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncAutoconfigServerLayer(AsyncLayerProcess):

    def __init__(
        self,
        linklayer: BasicLinkLayer,
        address: str = "127.0.0.1",
        registration_prefixes: List[Tuple[Name, bool]] = list(),
        log_level: int = 255,
    ):
        super().__init__(logger_name="AutoconfigLayer", log_level=log_level)
        self._core = AutoconfigServerCore(
            linklayer=linklayer,
            address=address,
            registration_prefixes=registration_prefixes,
            logger=self.logger,
        )

    @property
    def fib(self) -> BaseForwardingInformationBase:
        return self._core.fib

    @fib.setter
    def fib(self, value: BaseForwardingInformationBase):
        self._core.fib = value

    @property
    def rib(self) -> BaseRoutingInformationBase:
        return self._core.rib

    @rib.setter
    def rib(self, value: BaseRoutingInformationBase):
        self._core.rib = value

    async def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            await to_lower.put(out.item)
        elif out.direction == "higher":
            await to_higher.put(out.item)
        elif out.direction == "queue_lower":
            if self.queue_to_lower is not None:
                await self.queue_to_lower.put(out.item)
        elif out.direction == "queue_higher":
            if self.queue_to_higher is not None:
                await self.queue_to_higher.put(out.item)

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        for out in self._core.handle_from_higher(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            return
        fid: int = data[0]
        addr_info = self._core._linklayer.faceidtable.get_address_info(fid)
        packet: Packet = data[1]
        for out in self._core.handle_from_lower(fid, packet, addr_info):
            await self._apply_outbound(out, to_lower, to_higher)
