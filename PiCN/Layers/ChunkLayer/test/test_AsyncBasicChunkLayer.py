"""Async tests for AsyncBasicChunkLayer (Task 4.3).

Plain pytest module -- see ADR-010's Addendum.
"""

import asyncio

import pytest

from PiCN.Layers.ChunkLayer.AsyncBasicChunkLayer import AsyncBasicChunkLayer
from PiCN.Layers.ChunkLayer.ChunkLayerCore import RequestTableEntry
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Packets import Content, Interest, Name


class TestAsyncBasicChunkLayer:
    def setup_method(self):
        self.chunkifyer = SimpleContentChunkifyer()
        self.layer = AsyncBasicChunkLayer(self.chunkifyer, log_level=255)
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=32)

    @pytest.mark.asyncio
    async def test_interest_from_lower_served_from_chunk_table(self):
        n = Name("/test/data/c0")
        interest = Interest(n)
        content = Content(n, "dataobject")
        self.layer._core._chunk_table[content.name] = (content, 0.0)

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [0, interest])

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == 0
        assert packet == content
        assert self.to_higher.empty()

    @pytest.mark.asyncio
    async def test_small_content_round_trip_from_higher_and_lower(self):
        """Interest then small content: chunk layer forwards and reassembles pass-through."""
        name = Name("/test/data")
        interest = Interest(name)
        payload = Content(name, "content")

        await self.layer.data_from_higher(self.to_lower, self.to_higher, [0, interest])
        face_id, down_interest = self.to_lower.get_nowait()
        assert face_id == 0
        assert down_interest == interest

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [0, payload])
        face_id, up_content = self.to_higher.get_nowait()
        assert face_id == 0
        assert up_content == payload
        assert self.to_lower.empty()

    @pytest.mark.asyncio
    async def test_reassembled_chunks_delivered_to_higher(self):
        n1 = Name("/test/data")
        chunk1_n = Name("/test/data/c0")
        chunk2_n = Name("/test/data/c1")
        re1 = RequestTableEntry(n1)
        re1.chunked = True
        re1.requested_chunks.append(chunk1_n)
        re1.requested_chunks.append(chunk2_n)
        self.layer._core._request_table.append(re1)

        chunk1 = Content(chunk1_n, "chunk1")
        chunk2 = Content(chunk2_n, "chunk2")

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [0, chunk2])
        assert self.to_higher.empty()

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [0, chunk1])
        face_id, reassembled = self.to_higher.get_nowait()
        assert face_id == 0
        assert reassembled.name == n1
        assert reassembled.content == "chunk1chunk2"
