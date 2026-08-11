"""Test UDP4Interface's async contract (register()/send_async()), added
alongside its unchanged sync contract in Task 3.2. See
docs/design-adrs/ADR-008-baseinterface-contract.md.

Plain pytest module, not unittest.TestCase -- see ADR-010's Addendum:
pytest-asyncio's @pytest.mark.asyncio has no effect on unittest.TestCase
methods.
"""

import asyncio
import socket

import pytest

from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface


class TestUDP4InterfaceAsync:
    """Test UDP4Interface's async contract"""

    def setup_method(self):
        self.interface = UDP4Interface(0)

    def teardown_method(self):
        self.interface.close()

    @pytest.mark.asyncio
    async def test_send_async_after_register_reaches_a_real_socket(self):
        """register() followed by send_async(): a real UDP socket receives
        the data."""
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.bind(("0.0.0.0", 0))
        test_sock.setblocking(False)
        loop = asyncio.get_running_loop()

        queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        await self.interface.register(queue, interface_id=0)

        await self.interface.send_async(b"HelloAsyncWorld", ("127.0.0.1", test_sock.getsockname()[1]))

        data, addr = await asyncio.wait_for(loop.sock_recvfrom(test_sock, 8192), timeout=2.0)
        test_sock.close()

        assert data == b"HelloAsyncWorld"
        assert addr == ("127.0.0.1", self.interface.get_port())

    @pytest.mark.asyncio
    async def test_a_real_datagram_arrives_on_the_registered_queue(self):
        """A real UDP packet sent to the interface's port arrives on the
        queue as (data, addr, interface_id) with the interface_id given to
        register()."""
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.bind(("0.0.0.0", 0))

        queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        await self.interface.register(queue, interface_id=7)

        test_sock_port = test_sock.getsockname()[1]
        test_sock.sendto(b"HelloWorld", ("127.0.0.1", self.interface.get_port()))

        data, addr, interface_id = await asyncio.wait_for(queue.get(), timeout=2.0)
        test_sock.close()

        assert data == b"HelloWorld"
        assert addr == ("127.0.0.1", test_sock_port)
        assert interface_id == 7

    @pytest.mark.asyncio
    async def test_send_async_before_register_raises_runtime_error(self):
        """send_async() before register() raises RuntimeError, does not
        hang, and does not silently drop the data."""
        with pytest.raises(RuntimeError):
            await self.interface.send_async(b"too early", ("127.0.0.1", 1))

    @pytest.mark.asyncio
    async def test_datagram_received_drops_on_a_full_queue_without_blocking_or_crashing(self):
        """A queue passed with maxsize=1: filling it and then triggering a
        second datagram_received() does not raise out of the protocol
        callback and does not block the event loop -- the second item is
        dropped, not silently queued or crashed on."""
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.bind(("0.0.0.0", 0))

        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        await self.interface.register(queue, interface_id=0)

        test_sock.sendto(b"first", ("127.0.0.1", self.interface.get_port()))
        first_data, _addr, _iid = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert first_data == b"first"

        # Refill the queue to capacity, then trigger a second datagram while
        # it is still full -- this must not raise, hang, or block the loop.
        await queue.put((b"placeholder", ("127.0.0.1", 0), 0))
        test_sock.sendto(b"second", ("127.0.0.1", self.interface.get_port()))
        test_sock.close()

        # Give the event loop a turn to actually run datagram_received().
        await asyncio.sleep(0.1)

        assert queue.qsize() == 1
        remaining, _addr, _iid = queue.get_nowait()
        assert remaining == b"placeholder"
