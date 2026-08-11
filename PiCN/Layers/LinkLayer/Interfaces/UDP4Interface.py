"""Implementation of an Interface using UDP4 for communication"""

import asyncio
import logging
import socket

from typing import Optional

from PiCN.Layers.LinkLayer.Interfaces import BaseInterface

_logger = logging.getLogger(__name__)


class _UDP4DatagramProtocol(asyncio.DatagramProtocol):
    """asyncio.DatagramProtocol feeding datagrams into an interface's inbound
    queue. See UDP4Interface.register() and ADR-008's 2026-08-04 addendum.
    """

    def __init__(self, queue: asyncio.Queue, interface_id: int):
        self._queue = queue
        self._interface_id = interface_id

    def datagram_received(self, data: bytes, addr) -> None:
        # datagram_received() is a plain callback, not a coroutine -- it
        # cannot await queue.put(...) (ADR-005 rule 4 mandates await for
        # backpressure everywhere else). This is a deliberate, narrow
        # exception: UDP already has no delivery guarantee, so dropping a
        # datagram under backpressure is not the same "hides a real bug"
        # concern ADR-005 exists to prevent for inter-layer queues -- it is
        # UDP behaving like UDP. See ADR-008's 2026-08-04 addendum.
        try:
            self._queue.put_nowait((data, addr, self._interface_id))
        except asyncio.QueueFull:
            _logger.warning(
                "UDP4Interface %d: inbound queue full, dropping a datagram "
                "from %s", self._interface_id, addr,
            )


class UDP4Interface(BaseInterface):
    """Implementation of an Interface using UDP4 for communication
    :param listen

    Carries two coexisting method surfaces (ADR-008's 2026-08-04 addendum):
    the original synchronous send()/receive()/file_descriptor, used by
    SyncRunStrategy and unchanged since before the asyncio migration, and the
    newer register()/send_async(), used by AsyncRunStrategy. Both operate on
    the same already-bound socket.
    """

    def __init__(self, listen_port: int, buffersize: int=8192):
        self.listen_port = listen_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.listen_port))

        self._buffersize = buffersize
        self._transport: Optional[asyncio.DatagramTransport] = None

    def send(self, data, addr):
        self.sock.sendto(data, addr)

    def receive(self):
        data, addr = self.sock.recvfrom(self._buffersize)
        return data, addr

    async def register(self, queue: asyncio.Queue, interface_id: int) -> None:
        """Wire this interface's already-bound socket into the running
        asyncio event loop, so inbound datagrams are pushed onto queue as
        (data, addr, interface_id) instead of requiring a blocking
        receive()/select() call. Must be called from within a running event
        loop. See ADR-008.
        """
        loop = asyncio.get_running_loop()
        transport, _protocol = await loop.create_datagram_endpoint(
            lambda: _UDP4DatagramProtocol(queue, interface_id),
            sock=self.sock,
        )
        self._transport = transport

    async def send_async(self, data, addr) -> None:
        """The async counterpart to send(), used by AsyncRunStrategy. Named
        distinctly from send() rather than replacing it -- Python cannot
        dispatch on sync vs. async by signature alone, and send() must keep
        its exact synchronous behaviour for SyncRunStrategy (ADR-008's
        2026-08-04 addendum: both surfaces coexist on one class).
        """
        if self._transport is None:
            raise RuntimeError(
                "UDP4Interface.send_async() called before register(); "
                "there is no transport to send on."
            )
        self._transport.sendto(data, addr)

    @property
    def file_descriptor(self):
        return self.sock

    def get_port(self) -> int:
        """Returns port on which the Interface is running"""
        return int(self.sock.getsockname()[1])

    def close(self):
        self.sock.close()

    def enable_broadcast(self) -> bool:
        """
        Attempts to enable broadcasting on this interface.

        :return: True on success, False on failure
        """
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except:
            return False
        return True

    def get_broadcast_address(self) -> str:
        return '255.255.255.255'

    def __eq__(self, other):
        return self.get_port() == other.get_port()