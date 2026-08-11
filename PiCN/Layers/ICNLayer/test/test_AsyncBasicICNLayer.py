"""Async characterization-style tests for AsyncBasicICNLayer (Task 4.2).

Plain pytest module -- see ADR-010's Addendum. Mirrors
test_characterization.py scenarios against the async wrapper.
"""

import asyncio

import pytest

from PiCN.Layers.ICNLayer.AsyncBasicICNLayer import AsyncBasicICNLayer
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Packets import Content, Interest, Name, Nack, NackReason


class TestAsyncBasicICNLayer:
    def setup_method(self):
        self.layer = AsyncBasicICNLayer(log_level=255)
        self.layer.cs = ContentStoreMemoryExact()
        self.layer.fib = ForwardingInformationBaseMemoryPrefix()
        self.layer.pit = PendingInterstTableMemoryExact()
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=32)

    @pytest.mark.asyncio
    async def test_interest_from_lower_with_fib_entry_is_forwarded_to_lower(self):
        incoming_face_id = 2
        outgoing_face_id = 5
        name = Name("/test/data")
        interest = Interest("/test/data")
        self.layer.fib.add_fib_entry(name, [outgoing_face_id], static=True)

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [incoming_face_id, interest])

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == outgoing_face_id
        assert packet == interest
        assert self.to_higher.empty()
        pit_entry = self.layer.pit.find_pit_entry(name)
        assert pit_entry is not None
        assert incoming_face_id in pit_entry.faceids

    @pytest.mark.asyncio
    async def test_interest_from_lower_with_no_fib_entry_yields_nack_to_lower(self):
        incoming_face_id = 7
        interest = Interest("/no/such/route")

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [incoming_face_id, interest])

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == incoming_face_id
        assert isinstance(packet, Nack)
        assert packet.reason == NackReason.NO_ROUTE
        assert self.layer.pit.find_pit_entry(interest.name) is None

    @pytest.mark.asyncio
    async def test_content_from_lower_matching_pit_entry_is_forwarded_to_lower(self):
        name = Name("/test/data")
        interest = Interest("/test/data")
        waiting_face_id = 3
        arriving_face_id = 9
        content = Content("/test/data", "payload")
        self.layer.pit.add_pit_entry(name, waiting_face_id, interest, local_app=False)

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [arriving_face_id, content])

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == waiting_face_id
        assert packet == content
        assert self.layer.pit.find_pit_entry(name) is None
        assert self.layer.cs.find_content_object(name).content == content

    @pytest.mark.asyncio
    async def test_content_from_lower_with_no_pit_entry_is_silently_dropped(self):
        content = Content("/nobody/asked/for/this", "payload")
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [1, content])
        assert self.to_lower.empty()
        assert self.to_higher.empty()
        assert self.layer.cs.find_content_object(content.name) is None
