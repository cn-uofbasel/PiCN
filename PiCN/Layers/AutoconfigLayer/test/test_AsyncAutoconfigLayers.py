"""Async characterization-style tests for Autoconfig layers (Task 4.8)."""

import asyncio

import pytest

from PiCN.Layers.AutoconfigLayer.AsyncAutoconfigClientLayer import AsyncAutoconfigClientLayer
from PiCN.Layers.AutoconfigLayer.AsyncAutoconfigServerLayer import AsyncAutoconfigServerLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.AutoconfigLayer.test.mocks import MockInterface
from PiCN.Packets import Name, Interest, Content


class TestAsyncAutoconfigServerLayer:
    def setup_method(self):
        self.mock_interface = MockInterface(port=1337)
        self.faceidtable = FaceIDDict()
        self.linklayer = BasicLinkLayer([self.mock_interface], self.faceidtable)
        self.fib = ForwardingInformationBaseMemoryPrefix()
        self.layer = AsyncAutoconfigServerLayer(linklayer=self.linklayer, address="127.0.1.1")
        self.layer.fib = self.fib
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.layer.queue_to_lower = asyncio.Queue(maxsize=32)
        self.layer.queue_to_higher = asyncio.Queue(maxsize=32)

    @pytest.mark.asyncio
    async def test_pass_through_from_lower(self):
        self.faceidtable.add(42, AddressInfo(("127.13.37.42", 4567), 0))
        interest = Interest(Name("/foo/bar"))
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [42, interest])
        face_id, packet = self.to_higher.get_nowait()
        assert face_id == 42
        assert packet == interest

    @pytest.mark.asyncio
    async def test_forwarder_advertisement(self):
        self.faceidtable.add(42, AddressInfo(("127.13.37.42", 4242), 0))
        interest = Interest(Name("/autoconfig/forwarders"))
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [42, interest])
        face_id, packet = self.to_lower.get_nowait()
        assert face_id == 42
        assert isinstance(packet, Content)
        assert b"udp4://127.0.1.1:" in packet.content.encode("utf-8") if isinstance(packet.content, str) else packet.content


class TestAsyncAutoconfigClientLayer:
    def setup_method(self):
        self.mock_interface = MockInterface(port=1337)
        self.faceidtable = FaceIDDict()
        self.linklayer = BasicLinkLayer([self.mock_interface], self.faceidtable)
        self.layer = AsyncAutoconfigClientLayer(linklayer=self.linklayer, bcport=4242)
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.layer.queue_to_lower = asyncio.Queue(maxsize=32)
        self.layer.queue_to_higher = asyncio.Queue(maxsize=32)

    @pytest.mark.asyncio
    async def test_pass_through_from_lower(self):
        self.faceidtable.add(42, AddressInfo(("127.13.37.42", 4567), 0))
        interest = Interest(Name("/foo/bar"))
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [42, interest])
        face_id, packet = self.to_higher.get_nowait()
        assert face_id == 42
        assert packet == interest
