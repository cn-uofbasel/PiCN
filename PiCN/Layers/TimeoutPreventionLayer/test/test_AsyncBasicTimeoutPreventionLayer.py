"""Async characterization-style tests for AsyncBasicTimeoutPreventionLayer (Task 4.5)."""

import asyncio

import pytest

from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.TimeoutPreventionLayer.AsyncBasicTimeoutPreventionLayer import (
    AsyncBasicTimeoutPreventionLayer,
)
from PiCN.Layers.TimeoutPreventionLayer.TimeoutPreventionCore import TimeoutPreventionMessageDict
from PiCN.Packets import Content, Interest


class TestAsyncBasicTimeoutPreventionLayer:
    def setup_method(self):
        self.message_dict = TimeoutPreventionMessageDict()
        self.computation_table = NFNComputationList(None, None)
        self.layer = AsyncBasicTimeoutPreventionLayer(self.message_dict, self.computation_table, log_level=255)
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=32)

    @pytest.mark.asyncio
    async def test_keep_alive_request_replies_with_content_when_comp_running(self):
        """Mirrors test_keep_alive_request for the async wrapper."""
        interest = Interest("/test/func/_()/NFN")
        keep_alive = Interest("/test/func/_()/KEEPALIVE/NFN")
        content = Content(keep_alive.name)

        self.layer.computation_table.add_computation(interest.name, 3, interest)

        await self.layer.data_from_lower(self.to_lower, self.to_higher, [3, keep_alive])

        assert self.to_higher.empty()
        face_id, packet = self.to_lower.get_nowait()
        assert face_id == 3
        assert packet == content
