"""Async characterization-style tests for AsyncBasicRoutingLayer (Task 4.8)."""

import asyncio

import pytest

from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.RoutingLayer.AsyncBasicRoutingLayer import AsyncBasicRoutingLayer
from PiCN.Layers.RoutingLayer.RoutingInformationBase import TreeRoutingInformationBase
from PiCN.Layers.RoutingLayer.test.mocks import MockInterface
from PiCN.Packets import Content, Interest, Name


class TestAsyncBasicRoutingLayer:
    def setup_method(self):
        self.mock_interface = MockInterface(0)
        self.fidtable = FaceIDDict()
        self.linklayer = BasicLinkLayer([self.mock_interface], self.fidtable)
        self.fib = ForwardingInformationBaseMemoryPrefix()
        self.rib = TreeRoutingInformationBase()
        self.layer = AsyncBasicRoutingLayer(self.linklayer, ageing_interval=60.0)
        self.layer.rib = self.rib
        self.layer.fib = self.fib
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.layer.queue_to_lower = asyncio.Queue(maxsize=32)
        self.layer.queue_to_higher = asyncio.Queue(maxsize=32)

    @pytest.mark.asyncio
    async def test_pass_through_from_lower(self):
        interest = Interest(Name("/test1"))
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [42, interest])
        face_id, packet = self.layer.queue_to_higher.get_nowait()
        assert face_id == 42
        assert packet == interest

    @pytest.mark.asyncio
    async def test_routing_interest_reply(self):
        interest = Interest(Name("/routing"))
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [42, interest])
        face_id, packet = self.layer.queue_to_lower.get_nowait()
        assert face_id == 42
        assert packet == Content(Name("/routing"), bytes())

    @pytest.mark.asyncio
    async def test_pass_through_from_higher(self):
        interest = Interest(Name("/test2"))
        await self.layer.data_from_higher(self.to_lower, self.to_higher, [1337, interest])
        face_id, packet = self.layer.queue_to_lower.get_nowait()
        assert face_id == 1337
        assert packet == interest
