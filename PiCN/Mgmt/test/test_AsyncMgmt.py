"""Tests for AsyncMgmt (Task 5.1). Plain pytest + asyncio."""

import asyncio

import pytest

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import (
    ForwardingInformationBaseMemoryPrefix,
)
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.LinkLayer import AsyncBasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo, UDP4Interface
from PiCN.Mgmt.AsyncMgmt import AsyncMgmt
from PiCN.Packets import Name


async def _http_get(port: int, path: str) -> str:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(f"GET {path} HTTP/1.1\r\n\r\n".encode())
    await writer.drain()
    data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
    writer.close()
    await writer.wait_closed()
    return data.decode()


class TestAsyncMgmt:
    def setup_method(self):
        self.cs = ContentStoreMemoryExact()
        self.fib = ForwardingInformationBaseMemoryPrefix()
        self.pit = PendingInterstTableMemoryExact()
        self.iface = UDP4Interface(0)
        self.faceidtable = FaceIDDict()
        self.linklayer = AsyncBasicLinkLayer([self.iface], self.faceidtable)
        self.port = self.iface.get_port()
        self.shutdown_called = asyncio.Event()

        async def _on_shutdown():
            self.shutdown_called.set()

        self.mgmt = AsyncMgmt(
            self.cs, self.fib, self.pit, self.linklayer, self.port,
            shutdown=_on_shutdown,
        )

    async def teardown_async(self):
        await self.mgmt.stop()
        self.iface.close()

    @pytest.mark.asyncio
    async def test_newface(self):
        await self.mgmt.start()
        try:
            data = await _http_get(
                self.port, "/linklayer/newface/127.0.0.1:9000:0")
            assert data == (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "newface OK:0\r\n"
            )
            assert self.linklayer.faceidtable.get_num_entries() == 1
            assert self.linklayer.faceidtable.get_address_info(0) == AddressInfo(
                ("127.0.0.1", 9000), 0)
        finally:
            await self.teardown_async()

    @pytest.mark.asyncio
    async def test_newforwardingrule(self):
        await self.mgmt.start()
        try:
            data = await _http_get(
                self.port, "/icnlayer/newforwardingrule/%2Ftest%2Fdata:2")
            assert data == (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "newforwardingrule OK:2\r\n"
            )
            assert self.fib.find_fib_entry(Name("/test/data")).faceid == [2]
        finally:
            await self.teardown_async()

    @pytest.mark.asyncio
    async def test_newcontent(self):
        await self.mgmt.start()
        try:
            data = await _http_get(
                self.port, "/icnlayer/newcontent/%2Ftest%2Fdata:HelloWorld")
            assert data == (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "newcontent OK\r\n"
            )
            assert (
                self.cs.find_content_object(Name("/test/data")).content.content
                == "HelloWorld"
            )
        finally:
            await self.teardown_async()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_cleanly(self):
        await self.mgmt.start()
        try:
            data = await _http_get(self.port, "/shutdown")
            assert data == (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "shutdown\r\n"
            )
            await asyncio.wait_for(self.shutdown_called.wait(), timeout=2.0)
        finally:
            await self.mgmt.stop()
            self.iface.close()
        assert self.mgmt._serve_task is None
        assert self.mgmt._server is None
