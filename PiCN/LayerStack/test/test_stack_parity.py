"""Behavioral-parity test between the old multiprocessing LayerStack and the
new asyncio AsyncLayerStack.

Phase 2 introduces a brand-new execution model for layers (asyncio.Queue +
asyncio.Task instead of multiprocessing.Queue + multiprocessing.Process), but
claims to preserve the exact same OBSERVABLE contract: the same 3-layer stack
of identical layer logic must route data through the same queues in the same
directions with the same result. This file builds the identical scenario
twice -- once per execution model -- and checks the outputs match, so that
claim has direct test evidence rather than resting on code review alone.

This deliberately does NOT wire the two stacks together. Their queue types
(multiprocessing.Queue vs asyncio.Queue) are not interchangeable, and nothing
in the migration plan needs them to be: each ProgramLib switches its whole
stack from LayerStack to AsyncLayerStack at once (Phase 4/5), never
layer-by-layer within a single running stack. A side-by-side comparison is
the meaningful equivalent of "interop" here.

NOTE: the async half deliberately does NOT use unittest.TestCase -- see
docs/design-adrs/ADR-010-async-test-strategy.md, "Addendum": pytest-asyncio's
@pytest.mark.asyncio has no effect on unittest.TestCase methods.
"""

import asyncio
import unittest

import pytest

from PiCN.LayerStack import LayerStack
from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.Processes import LayerProcess
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess


class EchoLayerProcess(LayerProcess):
    """Old-style layer: tags data with the direction it travelled and passes
    it to the opposite side. Kept intentionally trivial -- the point of this
    file is to prove the STACK/lifecycle machinery is equivalent, not any
    particular layer's business logic (that is Phase 4's concern)."""

    def data_from_lower(self, to_lower, to_higher, data):
        to_higher.put(("from_lower", data))

    def data_from_higher(self, to_lower, to_higher, data):
        to_lower.put(("from_higher", data))


class EchoAsyncLayer(AsyncLayerProcess):
    """New-style layer with the SAME logic as EchoLayerProcess, so any
    difference in observed output is attributable to the stack/lifecycle
    machinery, not to different layer behaviour."""

    async def data_from_lower(self, to_lower, to_higher, data):
        await to_higher.put(("from_lower", data))

    async def data_from_higher(self, to_lower, to_higher, data):
        await to_lower.put(("from_higher", data))


class TestOldStackParity(unittest.TestCase):
    """The multiprocessing side of the comparison. A unittest.TestCase is
    fine here -- these tests are synchronous, not async."""

    def test_three_layer_echo_stack_routes_both_directions(self):
        top, mid, bottom = EchoLayerProcess(), EchoLayerProcess(), EchoLayerProcess()
        stack = LayerStack([top, mid, bottom])
        stack.start_all()
        try:
            stack.queue_from_higher.put("ping-down")
            result_down = stack.queue_to_lower.get(timeout=5)

            stack.queue_from_lower.put("ping-up")
            result_up = stack.queue_to_higher.get(timeout=5)
        finally:
            stack.stop_all()

        # Each of the 3 layers re-tags whatever it receives (including a
        # previous layer's own tag), so the result nests once per hop.
        self.assertEqual(result_down, ("from_higher", ("from_higher", ("from_higher", "ping-down"))))
        self.assertEqual(result_up, ("from_lower", ("from_lower", ("from_lower", "ping-up"))))


class TestNewStackParity:
    """The asyncio side of the identical comparison. Named with a capital T
    (not unittest.TestCase) -- see ADR-010's Addendum."""

    @pytest.mark.asyncio
    async def test_three_layer_echo_stack_routes_both_directions(self):
        top, mid, bottom = EchoAsyncLayer(), EchoAsyncLayer(), EchoAsyncLayer()
        stack = AsyncLayerStack([top, mid, bottom])
        stack.start_all()
        try:
            await stack.queue_from_higher.put("ping-down")
            result_down = await asyncio.wait_for(stack.queue_to_lower.get(), timeout=5)

            await stack.queue_from_lower.put("ping-up")
            result_up = await asyncio.wait_for(stack.queue_to_higher.get(), timeout=5)
        finally:
            await stack.stop_all()

        # Each of the 3 layers re-tags whatever it receives (including a
        # previous layer's own tag), so the result nests once per hop.
        assert result_down == ("from_higher", ("from_higher", ("from_higher", "ping-down")))
        assert result_up == ("from_lower", ("from_lower", ("from_lower", "ping-up")))
