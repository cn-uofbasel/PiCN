"""Async autoconfig repository layer wrapper (ADR-003)."""

import asyncio
from typing import Dict, Optional

from PiCN.Layers.AutoconfigLayer.AutoconfigLayerCore import AutoconfigRepoCore
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.RepositoryLayer.Repository.BaseRepository import BaseRepository
from PiCN.Packets import Name, Packet
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess
from PiCN.Processes.Outbound import Outbound


class AsyncAutoconfigRepoLayer(AsyncLayerProcess):

    def __init__(
        self,
        name: str,
        linklayer: BasicLinkLayer,
        repo: BaseRepository,
        addr: str,
        bcport: int = 9000,
        register_local: bool = True,
        register_global: bool = False,
        log_level: int = 255,
    ):
        super().__init__(logger_name="AutoconfigRepoLayer", log_level=log_level)
        self._core = AutoconfigRepoCore(
            name=name,
            linklayer=linklayer,
            repo=repo,
            addr=addr,
            bcport=bcport,
            register_local=register_local,
            register_global=register_global,
            logger=self.logger,
        )
        self._prefix_tasks: Dict[Name, asyncio.Task] = {}

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

    def start(self) -> asyncio.Task:
        task = super().start()
        asyncio.create_task(self._initial_forwarder_solicitations(), name="AutoconfigRepo-initial-solicit")
        return task

    async def _initial_forwarder_solicitations(self) -> None:
        for out in self._core.initial_forwarder_solicitations():
            await self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        for out in self._core.handle_from_higher(data):
            await self._apply_outbound(out, to_lower, to_higher)

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            return
        fid, packet = data
        addr_info = self._core._linklayer.faceidtable.get_address_info(fid)
        outbounds, renewals = self._core.handle_from_lower(fid, packet, addr_info)
        for out in outbounds:
            await self._apply_outbound(out, to_lower, to_higher)
        for regname, renewal_addr_info, delay in renewals:
            self._prefix_tasks[regname] = asyncio.create_task(
                self._renew_registration(regname, renewal_addr_info, delay),
                name=f"AutoconfigRepo-renew-{regname.to_string()}",
            )

    async def _renew_registration(self, name: Name, addr_info: AddressInfo, delay: float) -> None:
        await asyncio.sleep(delay)
        for out in self._core.send_service_registration(name, addr_info):
            await self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)

    async def stop(self, timeout: float = None) -> None:
        for task in self._prefix_tasks.values():
            task.cancel()
        for task in self._prefix_tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._prefix_tasks.clear()
        if timeout is None:
            from PiCN.Processes.AsyncLayerProcess import SHUTDOWN_TIMEOUT
            timeout = SHUTDOWN_TIMEOUT
        await super().stop(timeout=timeout)
