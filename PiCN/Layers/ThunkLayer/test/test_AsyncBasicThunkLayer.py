"""Async characterization-style tests for AsyncBasicThunkLayer (Task 4.7)."""

import asyncio

import pytest

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.ThunkLayer.AsyncBasicThunkLayer import AsyncBasicThunkLayer
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList
from PiCN.Packets import Content, Interest, Name, Nack, NackReason


class TestAsyncBasicThunkLayer:
    def setup_method(self):
        self.cs = ContentStoreMemoryExact()
        self.fib = ForwardingInformationBaseMemoryPrefix()
        self.pit = PendingInterstTableMemoryExact()
        self.faceidtable = FaceIDDict()
        self.thunk_table = ThunkList()
        self.parser = DefaultNFNParser()
        self.plan_table = PlanTable(self.parser)
        self.layer = AsyncBasicThunkLayer(
            self.cs,
            self.fib,
            self.pit,
            self.faceidtable,
            self.thunk_table,
            self.plan_table,
            self.parser,
            log_level=255,
        )
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.layer.queue_to_lower = asyncio.Queue(maxsize=32)
        self.layer.queue_to_higher = asyncio.Queue(maxsize=32)

    @pytest.mark.asyncio
    async def test_none_thunk_interest_from_lower_forwarded_to_higher(self):
        """Mirrors test_none_thunk_request_from_lower for the async wrapper."""
        interest = Interest("/test/data")
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [1, interest])
        face_id, packet = self.layer.queue_to_higher.get_nowait()
        assert face_id == 1
        assert packet == interest
        assert self.to_lower.empty()
        assert self.layer.queue_to_lower.empty()

    @pytest.mark.asyncio
    async def test_none_thunk_interest_from_higher_forwarded_to_lower(self):
        """Mirrors test_none_thunk_request_from_higher for the async wrapper."""
        interest = Interest("/test/data")
        await self.layer.data_from_higher(self.to_lower, self.to_higher, [1, interest])
        face_id, packet = self.to_lower.get_nowait()
        assert face_id == 1
        assert packet == interest
        assert self.to_higher.empty()

    @pytest.mark.asyncio
    async def test_thunk_request_for_data_in_cache(self):
        """Mirrors test_thunk_request_for_data_in_cache for the async wrapper."""
        self.layer.cs.add_content_object(Content(Name("/fct/f1"), "data"))
        interest = Interest(Name("/fct/f1/THUNK"))
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [3, interest])
        face_id, packet = self.layer.queue_to_lower.get_nowait()
        assert face_id == 3
        assert packet == Content(interest.name, str(4))

    @pytest.mark.asyncio
    async def test_remove_thunk_marker_matches_sync_layer(self):
        name = Name("/test/data/THUNK/NFN")
        ret = self.layer._core.removeThunkMarker(name)
        assert ret == Name("/test/data/NFN")
        assert name == Name("/test/data/THUNK/NFN")

    @pytest.mark.asyncio
    async def test_none_thunk_nack_from_lower_forwarded_to_higher(self):
        nack = Nack("/test/data", NackReason.NO_CONTENT, interest=Interest("/test/data"))
        await self.layer.data_from_lower(self.to_lower, self.to_higher, [1, nack])
        face_id, packet = self.layer.queue_to_higher.get_nowait()
        assert face_id == 1
        assert packet == nack
