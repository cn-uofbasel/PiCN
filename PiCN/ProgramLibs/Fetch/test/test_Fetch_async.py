"""Async Fetch smoke tests (Task 5.3)."""

import pytest

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Content, Name
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.runtime import Runtime


class TestFetchAsync:
    @pytest.mark.asyncio
    async def test_fetch_content_from_async_forwarder(self):
        encoder = SimpleStringEncoder(log_level=255)
        fwd = ICNForwarder(0, encoder=encoder, log_level=255, runtime=Runtime.ASYNC)
        port = fwd.linklayer.interfaces[0].get_port()
        await fwd.start_forwarder_async()

        fetch = Fetch(
            "127.0.0.1", port, log_level=255, encoder=encoder,
            runtime=Runtime.ASYNC)
        await fetch.start_fetch_async()
        try:
            # Seed CS via mgmt HTTP
            import asyncio
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(
                b"GET /icnlayer/newcontent/%2Ftest%2Fobj:HelloAsync HTTP/1.1\r\n\r\n")
            await writer.drain()
            await reader.read(1024)
            writer.close()
            await writer.wait_closed()

            result = await fetch.fetch_data_async(Name("/test/obj"), timeout=4.0)
            assert result == "HelloAsync"
        finally:
            await fetch.stop_fetch_async()
            await fwd.stop_forwarder_async()
            for iface in fwd.interfaces:
                iface.close()
            for iface in fetch.interfaces:
                iface.close()

    def test_async_fetch_does_not_start_in_init(self):
        fetch = Fetch("127.0.0.1", 9, runtime=Runtime.ASYNC)
        assert fetch.lstack.executor is None
        for iface in fetch.interfaces:
            iface.close()
