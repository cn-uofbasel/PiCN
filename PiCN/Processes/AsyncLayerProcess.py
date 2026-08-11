"""Abstract Class defining an asyncio-based layer

Async analogue of :class:`PiCN.Processes.LayerProcess.LayerProcess`. See
docs/design-adrs/ADR-003-handler-lifecycle.md and
docs/design-adrs/ADR-006-shutdown-cancellation.md for the design rationale.

This class does NOT inherit from :class:`PiCN.Processes.PiCNProcess.PiCNProcess`:
that base class's ``__getstate__``/``__setstate__`` pickling support and its
``.process`` attribute exist solely to let a layer object cross a
``multiprocessing`` process boundary. Under asyncio there is no such boundary
and nothing is pickled (see AGENTS.md), so that machinery would be dead weight
here.

Phase 2 introduces this class purely as new, additive infrastructure: no
production layer or ``LayerStack`` uses it yet. It is tested standalone, with
plain ``asyncio.Queue`` instances, until Phase 4 migrates real layers onto it.
"""

import abc
import asyncio
from typing import Optional

from PiCN.Logger import Logger

# Bound on how long stop() waits for the run loop to actually finish after
# being cancelled, before giving up and reporting a timeout. See ADR-006
# "Rules for implementers", #6 -- a named constant, not a literal.
SHUTDOWN_TIMEOUT = 5.0  # seconds


class AsyncLayerProcess(abc.ABC):
    """Abstract base class for a layer running as an asyncio Task.

    Subclasses implement :meth:`data_from_lower` and :meth:`data_from_higher`
    as coroutines (ADR-003). A single :meth:`run` loop replaces
    ``LayerProcess``'s three ``_run_*`` variants (ADR-004): it concurrently
    awaits both inbound queues and dispatches each item to the matching
    handler. Lifecycle is managed with :meth:`start`/:meth:`stop`, following
    the cancel-then-await pattern from ADR-006 -- no ``terminate()``, no
    ``time.sleep()``.
    """

    def __init__(self, logger_name: str = "AsyncLayerProcess", log_level: int = 255):
        self.logger = Logger(logger_name, log_level)
        self._queue_from_lower: Optional[asyncio.Queue] = None
        self._queue_from_higher: Optional[asyncio.Queue] = None
        self._queue_to_lower: Optional[asyncio.Queue] = None
        self._queue_to_higher: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None

    @property
    def queue_from_lower(self) -> Optional[asyncio.Queue]:
        """Queue to get data from the lower layer"""
        return self._queue_from_lower

    @queue_from_lower.setter
    def queue_from_lower(self, q: Optional[asyncio.Queue]) -> None:
        self._queue_from_lower = q

    @property
    def queue_from_higher(self) -> Optional[asyncio.Queue]:
        """Queue to get data from the higher layer"""
        return self._queue_from_higher

    @queue_from_higher.setter
    def queue_from_higher(self, q: Optional[asyncio.Queue]) -> None:
        self._queue_from_higher = q

    @property
    def queue_to_lower(self) -> Optional[asyncio.Queue]:
        """Queue to send data to the lower layer"""
        return self._queue_to_lower

    @queue_to_lower.setter
    def queue_to_lower(self, q: Optional[asyncio.Queue]) -> None:
        self._queue_to_lower = q

    @property
    def queue_to_higher(self) -> Optional[asyncio.Queue]:
        """Queue to send data to the higher layer"""
        return self._queue_to_higher

    @queue_to_higher.setter
    def queue_to_higher(self, q: Optional[asyncio.Queue]) -> None:
        self._queue_to_higher = q

    @abc.abstractmethod
    async def data_from_lower(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        """handle incoming data from the lower layer"""

    @abc.abstractmethod
    async def data_from_higher(self, to_lower: asyncio.Queue, to_higher: asyncio.Queue, data) -> None:
        """handle incoming data from the higher layer"""

    async def run(self) -> None:
        """Single run loop, replacing LayerProcess's _run_poll/_run_select/_run_sleep.

        Runs one pump task per direction (ADR-004, rule #1) and awaits both
        concurrently with asyncio.wait(FIRST_EXCEPTION), rather than nesting
        them in an asyncio.TaskGroup: TaskGroup wraps every child exception in
        an ExceptionGroup, even a single one, which would hide the original
        exception type from a supervising LayerStack (Task 2.4) and from
        anyone calling stop() after a crash. Propagating the exception
        unwrapped is what ADR-007's "log the full traceback, not str(exception)"
        and "the stack surfaces the exception" actually require.
        """

        async def _pump_lower() -> None:
            while True:
                data = await self.queue_from_lower.get()
                await self.data_from_lower(self.queue_to_lower, self.queue_to_higher, data)

        async def _pump_higher() -> None:
            while True:
                data = await self.queue_from_higher.get()
                await self.data_from_higher(self.queue_to_lower, self.queue_to_higher, data)

        tasks = []
        if self.queue_from_lower is not None:
            tasks.append(asyncio.create_task(_pump_lower()))
        if self.queue_from_higher is not None:
            tasks.append(asyncio.create_task(_pump_higher()))
        if not tasks:
            return

        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        except asyncio.CancelledError:
            # This run() task itself was cancelled (ADR-006). asyncio.wait()
            # does NOT cancel the tasks it was waiting on -- that is our job.
            for t in tasks:
                t.cancel()
            await asyncio.wait(tasks)
            raise

        for t in pending:
            t.cancel()
        if pending:
            await asyncio.wait(pending)

        for t in done:
            if t.cancelled():
                continue
            exc = t.exception()
            if exc is not None:
                raise exc

    def start(self) -> asyncio.Task:
        """Start this layer's run loop as a Task. Idempotent: calling this
        again while already running returns the SAME task rather than
        starting a second run loop. Must be called from within a running
        event loop.
        """
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run(), name=self.logger.name)
        return self._task

    async def stop(self, timeout: float = SHUTDOWN_TIMEOUT) -> None:
        """Cancel the run loop and wait for it to finish (ADR-006, rule #1).

        A no-op if the layer was never started (ADR-006, rule #4) -- calling
        stop() unconditionally during teardown must never raise.
        """
        if self._task is None:
            return
        task = self._task
        task.cancel()
        try:
            # Deliberately asyncio.wait([task], timeout=...), NOT
            # asyncio.wait_for(task, timeout=...): wait_for cancels the
            # CALLING coroutine's own wait on timeout, which only cancels
            # `task` a second time as a side effect of that -- if `task`
            # ignores cancellation (swallows it without re-raising, ADR-006
            # rule #2), wait_for keeps waiting for it to actually finish
            # regardless, hanging well past its nominal timeout.
            # asyncio.wait() returns at the deadline no matter what `task`
            # does internally, which is what "bounded" has to mean for this
            # to be a real safety net against exactly that failure mode.
            done, pending = await asyncio.wait([task], timeout=timeout)
            if pending:
                self.logger.warning(
                    "%s did not stop within %.1fs of being cancelled -- it may "
                    "be swallowing asyncio.CancelledError without re-raising "
                    "it (see ADR-006, rule #2).",
                    self.logger.name, timeout,
                )
            elif not task.cancelled():
                # Finished some other way (an exception, or -- degenerately --
                # a normal return). Surface it rather than losing it; a
                # caller explicitly awaiting stop() should see a crash that
                # already happened, not a silent no-op.
                exc = task.exception()
                if exc is not None:
                    raise exc
        finally:
            self._task = None
