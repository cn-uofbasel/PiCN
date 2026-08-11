"""Test AsyncLayerStack: construction, insert(), and bounded queue wiring.

NOTE: this file deliberately does NOT use unittest.TestCase for the async
tests. pytest-asyncio's @pytest.mark.asyncio has no effect on a coroutine
method defined on a unittest.TestCase subclass -- see
docs/design-adrs/ADR-010-async-test-strategy.md, "Addendum". The purely
synchronous construction/insert() tests below mirror test_LayerStack.py and
use plain pytest functions too, for consistency within this file.
"""

import asyncio
import logging

import pytest

from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack, DEFAULT_QUEUE_SIZE
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess


class ListHandler(logging.Handler):
    """Collects emitted LogRecords in a list. Used instead of pytest's caplog
    fixture: PiCN.Logger.Logger constructs a logging.Logger directly rather
    than via logging.getLogger(), so it is never registered in the standard
    logger hierarchy and nothing logged through it ever reaches caplog's
    root-attached handler, at any level. See the identical note in
    test_AsyncLayerProcess.py, where this was first discovered."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class DummyAsyncLayer(AsyncLayerProcess):
    """Minimal concrete AsyncLayerProcess for stack-wiring tests: echoes data
    across to the opposite side, same as AsyncLayerMock in
    test_AsyncLayerProcess.py.
    """

    def __init__(self):
        super().__init__()

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        await to_higher.put(data)

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        await to_lower.put(data)


class DistinctiveFailure(Exception):
    """A recognisable exception type, distinct from anything the stack or
    asyncio itself might raise, so tests can assert on IDENTITY rather than
    on a message string."""


class FailingAsyncLayer(AsyncLayerProcess):
    """A layer whose data_from_lower raises DistinctiveFailure for a specific
    trigger value, and otherwise behaves like DummyAsyncLayer."""

    def __init__(self, trigger: str):
        super().__init__()
        self._trigger = trigger

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        if data == self._trigger:
            raise DistinctiveFailure(data)
        await to_higher.put(data)

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        await to_lower.put(data)


class StubbornAsyncLayer(AsyncLayerProcess):
    """A layer that swallows cancellation indefinitely instead of re-raising
    it (deliberately violating ADR-006 rule #2). Used exclusively to prove
    stop_all()'s timeout path genuinely fires and is bounded -- see the
    identical, more thoroughly commented layer of the same name and purpose
    in test_AsyncLayerProcess.py."""

    def __init__(self):
        super().__init__(log_level=logging.WARNING)  # 255 ("off") would hide the warning under test
        self.entered = asyncio.Event()
        self.swallow_cancellation = True

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


def test_create_empty():
    with pytest.raises(ValueError):
        AsyncLayerStack([])


def test_create_single():
    layer = DummyAsyncLayer()
    lstack = AsyncLayerStack([layer])
    assert len(lstack.layers) == 1
    assert len(lstack.queues) == 0


def test_create_multiple():
    toplayer = DummyAsyncLayer()
    middlelayer = DummyAsyncLayer()
    bottomlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer, middlelayer, bottomlayer])
    assert len(lstack.layers) == 3
    assert len(lstack.queues) == 4
    assert toplayer.queue_to_lower is middlelayer.queue_from_higher
    assert toplayer.queue_from_lower is middlelayer.queue_to_higher
    assert middlelayer.queue_to_lower is bottomlayer.queue_from_higher
    assert middlelayer.queue_from_lower is bottomlayer.queue_to_higher
    assert toplayer.queue_to_lower is not bottomlayer.queue_from_higher
    assert toplayer.queue_from_lower is not bottomlayer.queue_to_higher


def test_insert_bottom():
    toplayer = DummyAsyncLayer()
    newlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer])
    lstack.insert(newlayer, below_of=toplayer)
    assert len(lstack.layers) == 2
    assert lstack.layers[0] is toplayer
    assert lstack.layers[1] is newlayer
    assert toplayer.queue_to_lower is newlayer.queue_from_higher
    assert toplayer.queue_from_lower is newlayer.queue_to_higher
    assert lstack.queue_to_lower is newlayer.queue_to_lower
    assert lstack.queue_from_lower is newlayer.queue_from_lower


def test_insert_top():
    bottomlayer = DummyAsyncLayer()
    newlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([bottomlayer])
    lstack.insert(newlayer, on_top_of=bottomlayer)
    assert len(lstack.layers) == 2
    assert lstack.layers[1] is bottomlayer
    assert lstack.layers[0] is newlayer
    assert bottomlayer.queue_to_higher is newlayer.queue_from_lower
    assert bottomlayer.queue_from_higher is newlayer.queue_to_lower
    assert lstack.queue_to_higher is newlayer.queue_to_higher
    assert lstack.queue_from_higher is newlayer.queue_from_higher


def test_insert_between():
    toplayer = DummyAsyncLayer()
    bottomlayer = DummyAsyncLayer()
    newlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer, bottomlayer])
    lstack.insert(newlayer, on_top_of=bottomlayer)
    assert len(lstack.layers) == 3
    assert lstack.layers[0] is toplayer
    assert lstack.layers[1] is newlayer
    assert lstack.layers[2] is bottomlayer
    assert toplayer.queue_to_lower is newlayer.queue_from_higher
    assert toplayer.queue_from_lower is newlayer.queue_to_higher
    assert bottomlayer.queue_to_higher is newlayer.queue_from_lower
    assert bottomlayer.queue_from_higher is newlayer.queue_to_lower
    assert toplayer.queue_to_lower is not bottomlayer.queue_from_higher
    assert toplayer.queue_from_lower is not bottomlayer.queue_to_higher


def test_insert_type_and_value_errors_preserved():
    """ADR-004 rule #4: insert()'s TypeError/ValueError behaviour for bad
    arguments must match LayerStack's exactly."""
    toplayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer])

    with pytest.raises(TypeError):
        lstack.insert(None, on_top_of=toplayer)
    with pytest.raises(TypeError):
        lstack.insert(DummyAsyncLayer())  # neither on_top_of nor below_of
    with pytest.raises(TypeError):
        lstack.insert(DummyAsyncLayer(), on_top_of=toplayer, below_of=toplayer)
    with pytest.raises(ValueError):
        lstack.insert(DummyAsyncLayer(), on_top_of=DummyAsyncLayer())  # not in the stack


def test_default_queue_size_applied_everywhere():
    """ADR-005 rule #3: LayerStack applies its queue size to every queue it creates."""
    toplayer = DummyAsyncLayer()
    middlelayer = DummyAsyncLayer()
    bottomlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer, middlelayer, bottomlayer])

    assert lstack.queue_to_higher.maxsize == DEFAULT_QUEUE_SIZE
    assert lstack.queue_from_higher.maxsize == DEFAULT_QUEUE_SIZE
    assert lstack.queue_to_lower.maxsize == DEFAULT_QUEUE_SIZE
    assert lstack.queue_from_lower.maxsize == DEFAULT_QUEUE_SIZE
    for q in lstack.queues:
        assert q.maxsize == DEFAULT_QUEUE_SIZE


def test_custom_queue_size_applied_everywhere():
    toplayer = DummyAsyncLayer()
    middlelayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer, middlelayer], queue_size=4)

    assert lstack.queue_to_higher.maxsize == 4
    assert lstack.queue_from_higher.maxsize == 4
    for q in lstack.queues:
        assert q.maxsize == 4

    newlayer = DummyAsyncLayer()
    lstack.insert(newlayer, on_top_of=toplayer)
    # A layer inserted afterwards must be wired with the SAME configured size,
    # not silently fall back to DEFAULT_QUEUE_SIZE.
    assert newlayer.queue_to_lower.maxsize == 4
    assert newlayer.queue_from_lower.maxsize == 4


@pytest.mark.asyncio
async def test_full_queue_blocks_put_until_drained():
    """ADR-005: a bounded queue's put() genuinely suspends when full, rather
    than raising or silently dropping the item."""
    toplayer = DummyAsyncLayer()
    bottomlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer, bottomlayer], queue_size=1)

    q = lstack.queue_from_lower  # the outer queue feeding the bottom layer from "below"
    await q.put("first")  # fills the queue (maxsize=1)

    blocked_put = asyncio.ensure_future(q.put("second"))
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(asyncio.shield(blocked_put), timeout=0.2)
    assert not blocked_put.done()

    # Draining one item must let the pending put() complete.
    assert await q.get() == "first"
    await asyncio.wait_for(blocked_put, timeout=1)
    assert await q.get() == "second"


@pytest.mark.asyncio
async def test_start_all_stop_all_round_trip():
    """A normal 3-layer stack: data flows top-to-bottom through both dummy
    layers, and stop_all() cleanly finishes every task within the timeout.
    """
    toplayer = DummyAsyncLayer()
    middlelayer = DummyAsyncLayer()
    bottomlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer, middlelayer, bottomlayer])

    lstack.start_all()
    try:
        await lstack.queue_from_higher.put("hello")
        result = await asyncio.wait_for(lstack.queue_to_lower.get(), timeout=1)
        assert result == "hello"
        assert lstack.exception is None
    finally:
        await lstack.stop_all()  # stop_all() already bounds itself via SHUTDOWN_TIMEOUT

    for task in lstack._tasks:
        assert task.done()


@pytest.mark.asyncio
async def test_layer_failure_cancels_siblings_and_surfaces():
    """ADR-007: an unhandled exception in one layer's handler cancels every
    other layer's task and is recorded on stack.exception, unwrapped."""
    toplayer = DummyAsyncLayer()
    failinglayer = FailingAsyncLayer(trigger="boom")
    bottomlayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer, failinglayer, bottomlayer])

    lstack.start_all()
    # Enter from the bottom so it reaches failinglayer.data_from_lower.
    await lstack.queue_from_lower.put("boom")

    async def _wait_for_failure():
        while lstack.exception is None:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_wait_for_failure(), timeout=1)

    assert isinstance(lstack.exception, DistinctiveFailure)

    async def _wait_for_siblings_cancelled():
        while not all(t.done() for t in lstack._tasks):
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_wait_for_siblings_cancelled(), timeout=1)
    for task, layer in zip(lstack._tasks, lstack.layers):
        if layer is failinglayer:
            assert not task.cancelled()  # this one failed, it wasn't cancelled
        else:
            assert task.cancelled()  # every sibling was cancelled


@pytest.mark.asyncio
async def test_stop_all_before_start_all_is_a_noop():
    lstack = AsyncLayerStack([DummyAsyncLayer()])
    await lstack.stop_all()  # must not raise


@pytest.mark.asyncio
async def test_insert_after_start_all_raises_runtime_error():
    """insert() must refuse to mutate a stack whose tasks are already
    running -- mirrors LayerStack's ProcessError case (ADR-004 area), even
    though only the TypeError/ValueError paths are an ADR-mandated match.

    NOTE: must be async -- start_all() calls asyncio.create_task(), which
    requires a running event loop.
    """
    toplayer = DummyAsyncLayer()
    lstack = AsyncLayerStack([toplayer])
    lstack.start_all()
    try:
        with pytest.raises(RuntimeError):
            lstack.insert(DummyAsyncLayer(), on_top_of=toplayer)
    finally:
        await lstack.stop_all()


@pytest.mark.asyncio
async def test_normal_shutdown_does_not_record_a_failure():
    """ADR-007 rule #3 in effect: cancellation during ordinary stop_all() is
    NOT a failure. _on_layer_done's early return for task.cancelled() fires
    for every layer here, and none of it may end up on stack.exception."""
    lstack = AsyncLayerStack([DummyAsyncLayer(), DummyAsyncLayer()])
    lstack.start_all()
    await lstack.stop_all()
    assert lstack.exception is None
    for task in lstack._tasks:
        assert task.cancelled()


@pytest.mark.asyncio
async def test_layer_failure_is_logged_with_traceback_not_stringified():
    """ADR-007 rule #4: a failing layer's exception must be logged with its
    traceback (exc_info=...), not just str(exception) -- a regression here
    would silently make production failures undebuggable."""
    toplayer = DummyAsyncLayer()
    failinglayer = FailingAsyncLayer(trigger="boom")
    lstack = AsyncLayerStack([toplayer, failinglayer])
    lstack.logger.setLevel(logging.ERROR)  # AsyncLayerStack's own logger defaults to 255 ("off")
    handler = ListHandler()
    lstack.logger.addHandler(handler)

    lstack.start_all()
    try:
        await lstack.queue_from_lower.put("boom")

        async def _wait_for_failure():
            while lstack.exception is None:
                await asyncio.sleep(0.01)

        await asyncio.wait_for(_wait_for_failure(), timeout=1)
    finally:
        await lstack.stop_all()

    records_with_traceback = [r for r in handler.records if r.exc_info is not None]
    assert records_with_traceback, (
        "expected a log record with exc_info set (ADR-007 rule #4); "
        f"captured records: {[r.getMessage() for r in handler.records]!r}"
    )
    assert records_with_traceback[0].exc_info[1] is lstack.exception


@pytest.mark.asyncio
async def test_stop_all_respects_timeout_for_a_stuck_layer():
    """ADR-006 addendum: stop_all() must genuinely return at its deadline
    even if a layer ignores cancellation, and must log a warning naming the
    stuck task rather than silently pretending everything stopped."""
    healthylayer = DummyAsyncLayer()
    stuck = StubbornAsyncLayer()
    lstack = AsyncLayerStack([healthylayer, stuck])
    lstack.logger.setLevel(logging.WARNING)  # AsyncLayerStack's own logger defaults to 255 ("off")
    handler = ListHandler()
    lstack.logger.addHandler(handler)

    lstack.start_all()
    await asyncio.wait_for(stuck.entered.wait(), timeout=1)
    stuck_task = lstack._tasks[lstack.layers.index(stuck)]

    try:
        start = asyncio.get_running_loop().time()
        await lstack.stop_all(timeout=0.1)
        elapsed = asyncio.get_running_loop().time() - start
        assert elapsed < 1.0, "stop_all() did not respect its timeout"

        assert not stuck_task.done(), "the stuck layer's task should still be running"
        messages = [r.getMessage() for r in handler.records]
        assert any("timed out" in m for m in messages), messages
    finally:
        # Cleanup so no task leaks past the end of the test (ADR-010 rule
        # #4). This must run even if an assertion above failed: asyncio's own
        # loop-teardown task cleanup does not bound its wait for a task that
        # ignores cancellation either (observed directly while writing this
        # test -- a leaked, immortal task here hung the whole run, not just
        # this test). Deliberately asyncio.wait(), NOT asyncio.wait_for(): the
        # latter has the exact bug documented in AsyncLayerProcess.stop() --
        # it was hit HERE too, in this cleanup code, before being fixed.
        stuck.swallow_cancellation = False
        stuck_task.cancel()
        await asyncio.wait([stuck_task], timeout=1)
