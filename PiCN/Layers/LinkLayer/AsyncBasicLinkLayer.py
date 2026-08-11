"""Async Link Layer for use inside AsyncLayerStack (Phase 5).

Promoted from RunStrategy._LinkLayerEngine. Unlike AsyncRunStrategy, this
layer runs in the node's event loop -- no forked child, no temporary
bridge executor. Interfaces push inbound datagrams onto queue_from_lower
via register(); outbound uses send_async().
"""

import asyncio
import concurrent.futures
import inspect
from typing import List, Optional

from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo, BaseInterface
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess


class AsyncBasicLinkLayer(AsyncLayerProcess):
    """Async link layer: faceidtable + interfaces, no select()/file_descriptor.

    :param interfaces: network interfaces (UDP4, Simulation, ...)
    :param faceidtable: face id mapping
    :param log_level: logger level
    """

    def __init__(self, interfaces: List[BaseInterface], faceidtable: BaseFaceIDTable,
                 log_level: int = 255):
        super().__init__(logger_name="LinkLayer", log_level=log_level)
        self.interfaces = interfaces
        self.faceidtable = faceidtable
        self.executor: Optional[concurrent.futures.Executor] = None
        self._registered = False

    def set_executor(self, executor: concurrent.futures.Executor) -> None:
        """Injected by AsyncLayerStack.start_all() (ADR-009)."""
        self.executor = executor

    async def _register_interfaces(self) -> None:
        if self._registered:
            return
        if self.queue_from_lower is None:
            raise RuntimeError(
                "AsyncBasicLinkLayer.queue_from_lower must be wired before start()"
            )
        for index, interface in enumerate(self.interfaces):
            register = interface.register
            # SimulationInterface.register requires an injected executor;
            # UDP4Interface.register does not.
            params = inspect.signature(register).parameters
            if "executor" in params:
                if self.executor is None:
                    raise RuntimeError(
                        "AsyncBasicLinkLayer needs an executor to register "
                        f"{type(interface).__name__} (ADR-009)"
                    )
                await register(self.queue_from_lower, interface_id=index,
                               executor=self.executor)
            else:
                await register(self.queue_from_lower, interface_id=index)
        self._registered = True

    async def run(self) -> None:
        await self._register_interfaces()
        await super().run()

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        """data is (packet, addr, interface_id) from an interface register() push."""
        packet, addr, interface_id = data
        addr_info = AddressInfo(addr, interface_id)
        faceid = self.faceidtable.get_or_create_faceid(addr_info)
        self.logger.info(
            "Got data from Network and from Face ID: " + str(faceid)
            + ", addr: " + str(addr_info.address)
        )
        item = [faceid, packet]
        if isinstance(to_higher, asyncio.Queue):
            await to_higher.put(item)
        else:
            # AsyncRunStrategy path: multiprocessing.Queue -- use executor.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, to_higher.put, item)

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        """Choose an interface via faceidtable and send_async."""
        faceid = data[0]
        packet = data[1]
        self.logger.info("Got data from Higher Layer with faceid: " + str(faceid))

        addr_info = self.faceidtable.get_address_info(faceid)
        if not addr_info:
            self.logger.error("No addr_info found for faceid: " + str(faceid))
            return
        try:
            await self.interfaces[addr_info.interface_id].send_async(
                packet, addr_info.address)
        except Exception:
            # Same deliberate except-Exception as BasicLinkLayer / Phase 3 engine
            # (preserve CancelledError; preserve observed error-message bugs).
            self.logger.error(
                "Could not sned packet to" + str(addr_info.address)
                + " Interface with ID" + addr_info.interface_id + " not available"
            )
        self.logger.info("Send packet to: " + str(addr_info.address))
