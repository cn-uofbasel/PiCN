"""Async tests for AsyncBasicRepositoryLayer (Task 4.4).

Plain pytest module -- see ADR-010's Addendum.
"""

import asyncio
import multiprocessing

import pytest

from PiCN.Layers.RepositoryLayer.AsyncBasicRepositoryLayer import AsyncBasicRepositoryLayer
from PiCN.Layers.RepositoryLayer.Repository import SimpleMemoryRepository
from PiCN.Packets import Content, Interest, Name, Nack, NackReason


class TestAsyncBasicRepositoryLayer:
    def setup_method(self):
        manager = multiprocessing.Manager()
        prefix = Name("/test/data")
        self.repository = SimpleMemoryRepository(prefix, manager)
        self.repository.add_content(Name("/test/data/f1"), "payload1")
        self.layer = AsyncBasicRepositoryLayer(self.repository, log_level=255)
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=8)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=8)
        self.layer.queue_to_lower = self.to_lower

    @pytest.mark.asyncio
    async def test_interest_returns_matching_content(self):
        interest = Interest("/test/data/f1")
        expected = Content("/test/data/f1", "payload1")

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [0, interest])

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == 0
        assert packet == expected
        assert self.to_higher.empty()

    @pytest.mark.asyncio
    async def test_missing_content_returns_nack(self):
        interest = Interest("/test/data/missing")
        expected = Nack(interest.name, NackReason.NO_CONTENT, interest=interest)

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [1, interest])

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == 1
        assert packet == expected
        assert self.to_higher.empty()

    @pytest.mark.asyncio
    async def test_wrong_prefix_returns_nack(self):
        interest = Interest("/other/data/f1")
        expected = Nack(interest.name, NackReason.NO_CONTENT, interest=interest)

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [2, interest])

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == 2
        assert packet == expected
