"""AsyncBasicLinkLayer inside AsyncLayerStack (Task 5.0).

No multiprocessing.Process -- the link layer runs in the test event loop.
Mirrors the packet-exchange scenarios of test_BasicLinkLayer_async.py.
"""

import asyncio
import socket

import pytest

from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.Layers.LinkLayer import AsyncBasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo, UDP4Interface


class TestAsyncBasicLinkLayer:
    """Packet exchange via AsyncBasicLinkLayer + AsyncLayerStack."""

    def setup_method(self):
        self.iface1 = UDP4Interface(0)
        self.face1 = FaceIDDict()
        self.ll1 = AsyncBasicLinkLayer([self.iface1], self.face1)
        self.stack1 = AsyncLayerStack([self.ll1])

        self.iface2 = UDP4Interface(0)
        self.face2 = FaceIDDict()
        self.ll2 = AsyncBasicLinkLayer([self.iface2], self.face2)
        self.stack2 = AsyncLayerStack([self.ll2])

        self.test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.test_sock.bind(("0.0.0.0", 0))
        self.test_port = self.test_sock.getsockname()[1]

    async def _stop_and_close(self):
        await self.stack1.stop_all()
        await self.stack2.stop_all()
        self.test_sock.close()
        self.iface1.close()
        self.iface2.close()

    @pytest.mark.asyncio
    async def test_receiving_a_packet(self):
        self.stack1.start_all()
        try:
            self.test_sock.sendto(
                b"HelloWorld", ("127.0.0.1", self.iface1.get_port()))
            data = await asyncio.wait_for(
                self.stack1.queue_to_higher.get(), timeout=2.0)
            faceid, content = data[0], data[1].decode()
            assert content == "HelloWorld"
            assert self.ll1.faceidtable.get_num_entries() == 1
            assert self.ll1.faceidtable.get_address_info(faceid).address[1] == self.test_port
            assert self.ll1.faceidtable.get_address_info(faceid).interface_id == 0
        finally:
            await self._stop_and_close()

    @pytest.mark.asyncio
    async def test_sending_a_packet(self):
        self.stack1.start_all()
        loop = asyncio.get_running_loop()
        self.test_sock.setblocking(False)
        try:
            fid = self.ll1.faceidtable.get_or_create_faceid(
                AddressInfo(("127.0.0.1", self.test_port), 0))
            await self.stack1.queue_from_higher.put([fid, b"HelloWorld"])
            data, _addr = await asyncio.wait_for(
                loop.sock_recvfrom(self.test_sock, 8192), timeout=2.0)
            assert data.decode() == "HelloWorld"
        finally:
            await self._stop_and_close()

    @pytest.mark.asyncio
    async def test_two_nodes_exchange_a_packet(self):
        """Two AsyncLayerStack nodes exchange a real UDP packet -- no Process."""
        self.stack1.start_all()
        self.stack2.start_all()
        try:
            fid = self.ll1.faceidtable.get_or_create_faceid(
                AddressInfo(("127.0.0.1", self.iface2.get_port()), 0))
            await self.stack1.queue_from_higher.put([fid, b"HelloWorld"])
            data = await asyncio.wait_for(
                self.stack2.queue_to_higher.get(), timeout=2.0)
            assert data[1].decode() == "HelloWorld"
            assert self.ll2.faceidtable.get_num_entries() == 1
        finally:
            await self._stop_and_close()
