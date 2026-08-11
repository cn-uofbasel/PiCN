"""Tests for AsyncLayerStack's ADR-009 executor ownership (Task 4.0).

Plain pytest module -- see ADR-010's Addendum.
"""

import asyncio
import concurrent.futures

import pytest

from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess


class DummyAsyncLayer(AsyncLayerProcess):
    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        await to_higher.put(data)

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        await to_lower.put(data)


class ExecutorAwareLayer(AsyncLayerProcess):
    """Opt-in layer that records the injected stack executor."""

    def __init__(self):
        super().__init__()
        self.executor = None

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        await to_higher.put(data)

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        await to_lower.put(data)


class TestAsyncLayerStackExecutor:
    """AsyncLayerStack owns exactly one ThreadPoolExecutor (ADR-009)."""

    @pytest.mark.asyncio
    async def test_start_all_creates_executor_and_stop_all_shuts_it_down(self):
        layer = DummyAsyncLayer()
        stack = AsyncLayerStack([layer])
        assert stack.executor is None

        stack.start_all()
        assert stack.executor is not None
        assert isinstance(stack.executor, concurrent.futures.ThreadPoolExecutor)
        held = stack.executor

        await stack.stop_all()
        assert stack.executor is None
        with pytest.raises(RuntimeError):
            held.submit(lambda: None)

    @pytest.mark.asyncio
    async def test_start_all_injects_executor_into_layers_that_opt_in(self):
        aware = ExecutorAwareLayer()
        plain = DummyAsyncLayer()
        stack = AsyncLayerStack([aware, plain])
        stack.start_all()
        try:
            assert aware.executor is stack.executor
            assert not hasattr(plain, "executor") or plain.__dict__.get("executor") is None
        finally:
            await stack.stop_all()

    @pytest.mark.asyncio
    async def test_executor_shuts_down_only_after_layers_stop(self):
        """Ordering: when executor.shutdown runs, every layer task is already done."""
        layer = DummyAsyncLayer()
        stack = AsyncLayerStack([layer])
        stack.start_all()
        executor = stack.executor
        original_shutdown = executor.shutdown
        seen = {}

        def tracking_shutdown(*args, **kwargs):
            seen["all_tasks_done"] = all(t.done() for t in stack._tasks)
            return original_shutdown(*args, **kwargs)

        executor.shutdown = tracking_shutdown
        await stack.stop_all()
        assert seen.get("all_tasks_done") is True
