"""Async ICNForwarder integration tests (Task 5.2)."""

import asyncio
import socket

import pytest

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Content, Interest, Name
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.runtime import Runtime


async def _http_get(port: int, path: str) -> str:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(f"GET {path} HTTP/1.1\r\n\r\n".encode())
    await writer.drain()
    data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
    writer.close()
    await writer.wait_closed()
    return data.decode()


class TestICNForwarderAsync:
    @pytest.mark.asyncio
    async def test_start_mgmt_content_interest_stop(self):
        encoder = SimpleStringEncoder(log_level=255)
        fwd = ICNForwarder(0, encoder=encoder, log_level=255, runtime=Runtime.ASYNC)
        port = fwd.linklayer.interfaces[0].get_port()
        await fwd.start_forwarder_async()
        try:
            data = await _http_get(
                port, "/icnlayer/newcontent/%2Ftest%2Fdata%2Fobject:HelloWorld")
            assert "newcontent OK" in data

            name = Name("/test/data/object")
            assert fwd.icnlayer.cs.find_content_object(name).content == Content(
                name, content="HelloWorld")

            interest = Interest("/test/data/object")
            encoded = encoder.encode(interest)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            sock.bind(("0.0.0.0", 0))
            loop = asyncio.get_running_loop()
            try:
                sock.sendto(encoded, ("127.0.0.1", port))
                encoded_content, _addr = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 8192), timeout=2.0)
                content = encoder.decode(encoded_content)
                assert content == Content(name, content="HelloWorld")
            finally:
                sock.close()
        finally:
            await fwd.stop_forwarder_async()
            for iface in fwd.interfaces:
                iface.close()

    @pytest.mark.asyncio
    async def test_sync_start_raises_on_async_runtime(self):
        fwd = ICNForwarder(0, runtime=Runtime.ASYNC)
        try:
            with pytest.raises(RuntimeError):
                fwd.start_forwarder()
        finally:
            for iface in fwd.interfaces:
                iface.close()
