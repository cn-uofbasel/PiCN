"""Async tests for AsyncBasicPacketEncodingLayer (Task 4.1).

Plain pytest module -- see ADR-010's Addendum.
"""

import asyncio

import pytest

from PiCN.Layers.PacketEncodingLayer.AsyncBasicPacketEncodingLayer import AsyncBasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Interest


class TestAsyncBasicPacketEncodingLayer:
    """Mirrors PacketEncoding characterization cases on the async wrapper."""

    def setup_method(self):
        self.layer = AsyncBasicPacketEncodingLayer(encoder=SimpleStringEncoder(), log_level=255)

    @pytest.mark.asyncio
    async def test_interest_from_higher_is_encoded_to_lower(self):
        to_lower: asyncio.Queue = asyncio.Queue(maxsize=8)
        to_higher: asyncio.Queue = asyncio.Queue(maxsize=8)
        interest = Interest("/test/data")

        await self.layer.data_from_higher(to_lower, to_higher, [2, interest])

        face_id, encoded = to_lower.get_nowait()
        assert face_id == 2
        assert encoded == self.layer.encode(interest)
        assert to_higher.empty()

    @pytest.mark.asyncio
    async def test_encoded_interest_from_lower_is_decoded_to_higher(self):
        to_lower: asyncio.Queue = asyncio.Queue(maxsize=8)
        to_higher: asyncio.Queue = asyncio.Queue(maxsize=8)
        interest = Interest("/test/data")
        encoded = self.layer.encode(interest)

        await self.layer.data_from_lower(to_lower, to_higher, [3, encoded])

        face_id, decoded = to_higher.get_nowait()
        assert face_id == 3
        assert decoded == interest
        assert to_lower.empty()

    @pytest.mark.asyncio
    async def test_malformed_wrong_length_is_dropped(self):
        to_lower: asyncio.Queue = asyncio.Queue(maxsize=8)
        to_higher: asyncio.Queue = asyncio.Queue(maxsize=8)

        await self.layer.data_from_higher(to_lower, to_higher, [1])

        assert to_lower.empty()
        assert to_higher.empty()
