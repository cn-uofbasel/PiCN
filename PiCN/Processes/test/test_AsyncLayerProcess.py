"""Test the abstract async layer base class AsyncLayerProcess

NOTE: this file deliberately does NOT use unittest.TestCase, unlike most of
the suite. pytest-asyncio's @pytest.mark.asyncio has no effect on a coroutine
method defined on a unittest.TestCase subclass -- pytest hands those to
unittest's own runner, which calls the coroutine, discards the resulting
coroutine object without awaiting it, and reports the test as passed without
ever running its body. See docs/design-adrs/ADR-010-async-test-strategy.md,
"Addendum". Do not change this file back to unittest.TestCase.
"""

import asyncio
import logging
import time

import pytest

from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess


class AsyncLayerMock(AsyncLayerProcess):
    """Mock implementation of an AsyncLayerProcess: mirrors LayerMock in
    test_LayerProcess.py, crossing the data over from one side to the other.
    """

    def __init__(self):
        super().__init__()

    async def data_from_lower(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        await to_higher.put(data)

    async def data_from_higher(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        await to_lower.put(data)


class ConcurrentAsyncLayer(AsyncLayerProcess):
    """A layer whose data_from_lower blocks until explicitly released, used
    to prove run() services both directions CONCURRENTLY (ADR-004 rule #1:
    one task per direction) rather than serially in a single loop -- if it
    were serial, data_from_higher would never get a chance to run while
    data_from_lower is blocked.
    """

    def __init__(self):
        super().__init__()
        self.lower_entered = asyncio.Event()
        self.lower_release = asyncio.Event()

    async def data_from_lower(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        self.lower_entered.set()
        await self.lower_release.wait()
        await to_higher.put(data)

    async def data_from_higher(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        await to_lower.put(data)


class ListHandler(logging.Handler):
    """Collects emitted LogRecords in a list. Used instead of pytest's caplog
    fixture: PiCN.Logger.Logger constructs a logging.Logger directly rather
    than via logging.getLogger(), so it is never registered in the standard
    logger hierarchy -- its `.parent` is never set, so nothing logged through
    it ever propagates to the root logger. caplog attaches to the root
    logger and so silently sees nothing from any PiCN.Logger.Logger instance
    at any level, regardless of caplog.at_level(...). Attaching a handler
    directly to the logger instance under test sidesteps this entirely.
    """

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class StubbornAsyncLayer(AsyncLayerProcess):
    """A layer that swallows cancellation instead of re-raising it
    (deliberately violating ADR-006 rule #2) for as long as
    swallow_cancellation is True. Used exclusively to prove stop()'s timeout
    path genuinely fires for a non-compliant layer -- no compliant layer
    should ever hit it. Swallows indefinitely (not just once): stop() is now
    implemented with asyncio.wait(..., timeout=...), which returns at the
    deadline regardless of how many times the task ignores cancellation (see
    ADR-006's addendum -- an earlier asyncio.wait_for()-based version could
    hang well past its nominal timeout against exactly this scenario).
    """

    def __init__(self):
        # NOTE: log_level=logging.WARNING, NOT the usual 255 ("off") used
        # elsewhere in this file -- this test asserts on a WARNING actually
        # being logged, and 255 exceeds even CRITICAL, silently filtering
        # every record at the source before it ever reaches caplog.
        super().__init__(log_level=logging.WARNING)
        self.swallow_cancellation = True
        self.entered = asyncio.Event()

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        pass

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        pass

    async def run(self) -> None:
        while True:
            self.entered.set()
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                if not self.swallow_cancellation:
                    raise


class CrashingAsyncLayer(AsyncLayerProcess):
    """A layer whose run() raises immediately, used to prove stop() surfaces
    a crash the task already ended with (rather than treating any already-
    finished task as a quiet, successful stop)."""

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        pass

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        pass

    async def run(self) -> None:
        raise RuntimeError("boom")


class TestAsyncLayerProcess:
    """Test the abstract async layer base class AsyncLayerProcess.

    Named with a capital T (unlike this repo's usual test_ClassName
    convention): pytest only auto-collects bare classes matching its default
    python_classes pattern ("Test*"). unittest.TestCase subclasses are exempt
    from that pattern -- pytest discovers them via inheritance instead -- which
    is why the rest of the suite gets away with lowercase names. A bare class
    has no such exemption.
    """

    def setup_method(self):
        self.q_from_higher: asyncio.Queue = asyncio.Queue()
        self.q_from_lower: asyncio.Queue = asyncio.Queue()
        self.q_to_higher: asyncio.Queue = asyncio.Queue()
        self.q_to_lower: asyncio.Queue = asyncio.Queue()

        self.layer: AsyncLayerMock = AsyncLayerMock()
        self.layer.queue_from_higher = self.q_from_higher
        self.layer.queue_from_lower = self.q_from_lower
        self.layer.queue_to_higher = self.q_to_higher
        self.layer.queue_to_lower = self.q_to_lower

    @pytest.mark.asyncio
    async def test_from_higher_to_lower(self):
        """Test correct handling from Higher to Lower"""
        self.layer.start()
        try:
            await self.q_from_higher.put("Testdata")
            output = await asyncio.wait_for(self.q_to_lower.get(), timeout=1)
            assert output == "Testdata"
        finally:
            await self.layer.stop()

    @pytest.mark.asyncio
    async def test_from_lower_to_higher(self):
        """Test correct handling from Lower to Higher"""
        self.layer.start()
        try:
            await self.q_from_lower.put("Testdata")
            output = await asyncio.wait_for(self.q_to_higher.get(), timeout=1)
            assert output == "Testdata"
        finally:
            await self.layer.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_a_noop(self):
        """ADR-006, rule #4: stop() on a layer that never started must not raise."""
        await self.layer.stop()

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self):
        """Calling start() again while already running returns the SAME task
        rather than creating a second run loop.
        """
        task_one = self.layer.start()
        task_two = self.layer.start()
        try:
            assert task_one is task_two
        finally:
            await self.layer.stop()

    @pytest.mark.asyncio
    async def test_stop_actually_stops_the_loop(self):
        """After stop() returns, the task is done and no further item placed
        on a queue is ever processed.
        """
        task = self.layer.start()
        await self.q_from_lower.put("before-stop")
        await asyncio.wait_for(self.q_to_higher.get(), timeout=1)

        await self.layer.stop()
        assert task.done()

        await self.q_from_lower.put("after-stop")
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(self.q_to_higher.get(), timeout=0.2)

    @pytest.mark.asyncio
    async def test_run_services_both_directions_concurrently(self):
        """ADR-004 rule #1: both inbound queues are awaited concurrently, one
        task per direction -- data_from_higher must still be serviced while
        data_from_lower is mid-flight and blocked.
        """
        layer = ConcurrentAsyncLayer()
        layer.queue_from_higher = self.q_from_higher
        layer.queue_from_lower = self.q_from_lower
        layer.queue_to_higher = self.q_to_higher
        layer.queue_to_lower = self.q_to_lower

        layer.start()
        try:
            await self.q_from_lower.put("slow")
            await asyncio.wait_for(layer.lower_entered.wait(), timeout=1)
            # data_from_lower is now blocked awaiting release. If run() were
            # serial (a single loop dispatching one direction at a time)
            # this next line would hang until timeout, since nothing would
            # ever get back around to servicing queue_from_higher.
            await self.q_from_higher.put("fast")
            result = await asyncio.wait_for(self.q_to_lower.get(), timeout=1)
            assert result == "fast"

            layer.lower_release.set()
            result2 = await asyncio.wait_for(self.q_to_higher.get(), timeout=1)
            assert result2 == "slow"
        finally:
            await layer.stop()

    @pytest.mark.asyncio
    async def test_stop_logs_and_returns_on_timeout_for_a_stuck_layer(self):
        """ADR-006 addendum: stop()'s timeout branch must log a warning
        (not just silently pass) when a layer fails to stop in time.
        """
        layer = StubbornAsyncLayer()
        handler = ListHandler()
        layer.logger.addHandler(handler)
        task = layer.start()
        await asyncio.wait_for(layer.entered.wait(), timeout=1)  # let it actually start running first
        try:
            start = time.monotonic()
            await layer.stop(timeout=0.1)
            elapsed = time.monotonic() - start
            assert elapsed < 1.0, "stop() did not respect its timeout"
            assert not task.done(), (
                "the task should still be running -- it never stops "
                "swallowing cancellation -- proving stop() genuinely timed "
                "out rather than cleanly stopping"
            )
            messages = [r.getMessage() for r in handler.records]
            assert any("did not stop within" in m for m in messages), (
                f"expected a warning naming the timeout (ADR-006 addendum); "
                f"captured messages were: {messages!r}"
            )
        finally:
            # Cleanup: stop swallowing and cancel again, so this actually
            # terminates the task instead of leaking it past the end of the
            # test (ADR-010 rule #4).
            layer.swallow_cancellation = False
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=1)
            assert task.done()

    @pytest.mark.asyncio
    async def test_stop_reraises_an_exception_the_task_already_crashed_with(self):
        """If the layer's task already ended in an exception (not
        cancellation) before stop() is called, stop() must surface it rather
        than silently treating an already-finished task as a quiet, clean
        stop -- a caller awaiting stop() should learn about a crash that
        already happened.
        """
        layer = CrashingAsyncLayer()
        task = layer.start()
        with pytest.raises(RuntimeError, match="boom"):
            await asyncio.wait_for(task, timeout=1)  # let it actually crash first
        assert task.done()

        with pytest.raises(RuntimeError, match="boom"):
            await layer.stop()
