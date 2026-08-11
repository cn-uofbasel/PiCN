"""Test SimulationInterface's async contract (register()/send_async()),
added alongside its unchanged sync contract in Task 3.5. See
docs/design-adrs/ADR-008-baseinterface-contract.md rule 7: UDP4Interface
first (Task 3.2), then the simulation interface.

SimulationBus itself is unchanged -- these tests exercise SimulationInterface
directly, simulating what SimulationBus would push, exactly like
test_UDP4Interface_async.py exercises UDP4Interface directly without a real
BasicLinkLayer.

Plain pytest module, not unittest.TestCase -- see ADR-010's Addendum.
"""

import asyncio
import concurrent.futures

import pytest

from PiCN.Layers.LinkLayer.Interfaces import SimulationInterface


class TestSimulationInterfaceAsync:
    """Test SimulationInterface's async contract"""

    def setup_method(self):
        self.interface = SimulationInterface("node-a")
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def teardown_method(self):
        # register()'s background pump blocks on queue_from_bus.get().
        # Push a dummy item so executor.shutdown(wait=True) does not hang
        # (ADR-009: cancellation does not stop a worker mid-flight).
        self.interface.queue_from_bus.put(["teardown", b""])
        self.executor.shutdown(wait=True)
        self.interface.close()

    @pytest.mark.asyncio
    async def test_a_bus_pushed_item_arrives_on_the_registered_queue(self):
        """register() + a manual queue_from_bus.put(...) (simulating what
        SimulationBus would do): the item arrives on the given asyncio.Queue
        as (packet, addr, interface_id)."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        await self.interface.register(queue, interface_id=5, executor=self.executor)

        # This is exactly the shape SimulationBus.send(packet, src_addr, "bus")
        # produces on the wire today -- [addr, data].
        self.interface.queue_from_bus.put(["node-b", b"HelloWorld"])

        packet, addr, interface_id = await asyncio.wait_for(queue.get(), timeout=2.0)

        assert packet == b"HelloWorld"
        assert addr == "node-b"
        assert interface_id == 5

    @pytest.mark.asyncio
    async def test_send_async_reaches_queue_from_linklayer(self):
        """send_async(): the data appears on queue_from_linklayer, matching
        what SimulationBus's receive("bus") side expects today."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        await self.interface.register(queue, interface_id=0, executor=self.executor)

        await self.interface.send_async(b"HelloWorld", "node-b")

        addr, data = self.interface.queue_from_linklayer.get(timeout=2.0)
        assert addr == "node-b"
        assert data == b"HelloWorld"

    @pytest.mark.asyncio
    async def test_send_async_before_register_raises_runtime_error(self):
        with pytest.raises(RuntimeError):
            await self.interface.send_async(b"too early", "node-b")
