"""Data Structure for managing AsyncLayerProcess layers and their queues

Async analogue of :class:`PiCN.LayerStack.LayerStack.LayerStack`. See
docs/design-adrs/ADR-004-async-layerstack.md and
docs/design-adrs/ADR-005-queue-bounding.md for the design rationale.

Phase 2 introduces this class purely as new, additive infrastructure: no
production layer or node type wires itself up with it yet (Task 2.3 covers
construction and queue wiring only; Task 2.4 adds start_all()/stop_all() and
failure supervision). The existing LayerStack keeps running every real layer
unchanged until Phase 4 migrates them one at a time.
"""

import asyncio
import concurrent.futures
from typing import List, Optional

from PiCN.Logger import Logger
from PiCN.Processes.AsyncLayerProcess import SHUTDOWN_TIMEOUT, AsyncLayerProcess

# PROVISIONAL -- not derived from measurement. See ADR-005 "Choosing the bound".
# Replace once per-queue depth has been measured under a representative run.
DEFAULT_QUEUE_SIZE = 128

# Default worker count for the stack-owned executor (ADR-009). Sized for a
# handful of concurrent blocking I/O / CPU dispatches, not one-per-layer.
DEFAULT_EXECUTOR_WORKERS = 4


class AsyncLayerStack(object):
    """
    Data structure for managing AsyncLayerProcess layers and the bounded
    asyncio.Queue pairs connecting them.
    """

    def __init__(self, layers: List[AsyncLayerProcess], queue_size: int = DEFAULT_QUEUE_SIZE,
                 executor_workers: int = DEFAULT_EXECUTOR_WORKERS):
        """
        Create a layer stack from a list of layers, where the topmost layer is the first element in the list.
        :param layers: List of layers to stack onto each other.
        :param queue_size: maxsize applied to every asyncio.Queue this stack creates (ADR-005).
                            Every queue is bounded; there is no way to construct an unbounded one here.
        :param executor_workers: max_workers for the ThreadPoolExecutor created at start_all()
                            (ADR-009). The pool itself is not created in __init__.
        """
        self.logger = Logger("AsyncLayerStack", 255)
        self.queue_size = queue_size
        self._executor_workers = executor_workers
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self.layers: List[AsyncLayerProcess] = []
        self.queues: List[asyncio.Queue] = []
        self._tasks: List[asyncio.Task] = []
        self.exception: Optional[BaseException] = None
        self._queue_to_higher = asyncio.Queue(maxsize=queue_size)
        self._queue_from_higher = asyncio.Queue(maxsize=queue_size)
        self._queue_to_lower = asyncio.Queue(maxsize=queue_size)
        self._queue_from_lower = asyncio.Queue(maxsize=queue_size)
        self.__started = False
        if len(layers) == 0:
            raise ValueError('Can\'t have an empty LayerStack')
        # Setup queues for each pair of layers
        for i in range(len(layers) - 1):
            upper = layers[i]
            lower = layers[i + 1]
            # Create two queues for communication
            q_to_upper = asyncio.Queue(maxsize=queue_size)
            q_to_lower = asyncio.Queue(maxsize=queue_size)
            upper.queue_to_lower = q_to_lower
            upper.queue_from_lower = q_to_upper
            lower.queue_to_higher = q_to_upper
            lower.queue_from_higher = q_to_lower
            # Append layers and queues to resource lists
            self.layers.append(upper)
            self.queues.append(q_to_upper)
            self.queues.append(q_to_lower)
        # Append last layer to resource list
        self.layers.append(layers[len(layers) - 1])
        self.layers[0].queue_to_higher = self.queue_to_higher
        self.layers[0].queue_from_higher = self.queue_from_higher
        self.layers[len(self.layers) - 1].queue_to_lower = self.queue_to_lower
        self.layers[len(self.layers) - 1].queue_from_lower = self.queue_from_lower

    @property
    def executor(self) -> Optional[concurrent.futures.ThreadPoolExecutor]:
        """The stack-owned executor, or None before start_all() / after shutdown."""
        return self._executor

    def insert(self, layer: AsyncLayerProcess, on_top_of: AsyncLayerProcess = None, below_of: AsyncLayerProcess = None):
        """
        Insert a layer into the layer stack, placing it on top of or beneath another layer. Either on_top_of or below_of
        must be provided.
        :param layer: The layer to insert.
        :param on_top_of: The layer on top of which the new layer should be inserted. Must not be used together with
                          below_of.
        :param below_of: The layer beneath of which the new layer should be inserted. Must not be used together with
                          on_top_of.
        :raises RuntimeError if this method is called after the layer stack was started.
        :raises TypeError if the layer to insert is None, or on_top_of and below_of are used together.
        :raises ValueError if on_top_of/below_of is not a layer in this LayerStack.
        """
        if self.__started:
            # LayerStack (multiprocessing) raises multiprocessing.ProcessError here; there is no
            # process concept under asyncio, so this uses a plain RuntimeError instead (ADR-004
            # preserves insert()'s TypeError/ValueError behaviour exactly, but does not mandate
            # matching this exception type, since it is not part of that contract).
            raise RuntimeError('AsyncLayerStack should not be changed after its tasks were started.')
        if layer is None:
            raise TypeError('Layer is None.')
        # Make sure that exactly one out of on_top_of, below_of is provided.
        if (on_top_of is None) == (below_of is None):
            raise TypeError('Needs either on_top_of xor below_of')
        insert_above: bool = on_top_of is not None
        ref_layer = on_top_of if insert_above else below_of
        # Find position of the reference layer
        for i in range(len(self.layers)):
            if self.layers[i] == ref_layer:
                # If the new layer should be inserted above the reference layer, it should be placed at the current
                # position of the reflayer, pushing the reflayer and following down by one. Else the reflayer should
                # remain at its position, only subsequent layers should be pushed down by one.
                if insert_above:
                    self.__insert(layer, i)
                else:
                    self.__insert(layer, i + 1)
                return
        raise ValueError('Reference layer is not in the layer stack.')

    def _inject_executor(self, layer: AsyncLayerProcess) -> None:
        """Give layer the stack executor if it opts in (ADR-009). Layers without
        an executor attribute or set_executor method are left alone -- not every
        layer needs one (e.g. PacketEncoding)."""
        set_executor = getattr(layer, "set_executor", None)
        if callable(set_executor):
            set_executor(self._executor)
            return
        if hasattr(layer, "executor"):
            layer.executor = self._executor

    def start_all(self) -> None:
        """
        Start every layer's run loop as a supervised asyncio.Task (ADR-007).
        Creates the stack-owned executor first (ADR-009), then starts tasks.
        Must be called from within a running event loop.
        """
        self.__started = True
        # Startup order (ADR-009): create the executor -> start layer tasks.
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._executor_workers)
        for layer in self.layers:
            self._inject_executor(layer)
            task = layer.start()
            task.add_done_callback(self._on_layer_done)
            self._tasks.append(task)

    def _on_layer_done(self, task: asyncio.Task) -> None:
        """Done-callback attached to every layer task. Cancellation is normal
        shutdown (ADR-006) and is not a failure. Any other exception is
        logged with its full traceback (ADR-007 rule #4 -- never just
        str(exception)), recorded as the stack's first failure, and every
        other still-running layer is cancelled so a broken node stops loudly
        instead of hanging on a queue that will never drain again.
        """
        if task.cancelled():
            return
        exc = task.exception()
        if exc is None:
            return
        self.logger.error("Layer task %r failed", task.get_name(), exc_info=exc)
        if self.exception is None:
            self.exception = exc
        for other in self._tasks:
            if other is not task and not other.done():
                other.cancel()

    async def stop_all(self, timeout: float = SHUTDOWN_TIMEOUT) -> None:
        """
        Cancel every layer's task and wait for all of them to finish, bounded
        by a single timeout for the whole stack (ADR-006). Then shut down the
        stack executor (ADR-009: after tasks stop, never before). A no-op if
        start_all() was never called.
        """
        if not self._tasks:
            if self._executor is not None:
                self._executor.shutdown(wait=True)
                self._executor = None
            return
        for task in self._tasks:
            task.cancel()
        # asyncio.wait(), NOT asyncio.wait_for(gather(...)): see the detailed
        # comment in AsyncLayerProcess.stop() -- wait_for only cancels the
        # CALLING coroutine on timeout, and gather()/wait_for() then keep
        # waiting for the real tasks to actually finish regardless, which
        # hangs indefinitely if any of them ignores cancellation. asyncio.wait()
        # returns at the deadline no matter what the tasks do internally.
        done, pending = await asyncio.wait(self._tasks, timeout=timeout)
        if pending:
            stuck = [t.get_name() for t in pending]
            self.logger.warning(
                "stop_all() timed out after %.1fs; %d layer task(s) did not "
                "stop: %s", timeout, len(stuck), stuck,
            )
        # Shutdown order (ADR-009): cancel -> await layers -> then executor.
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
    # NOTE: LayerStack's equivalent setters below assign via "self.queue_to_higher
    # = queue" inside the queue_to_higher setter itself -- a pre-existing infinite
    # recursion bug in the multiprocessing version, never triggered because nothing
    # calls these setters today. These setters assign to the backing "_"-prefixed
    # attribute instead. This is new code, not a port of that bug (ADR-001 only
    # binds characterization of OBSERVED behaviour; an unreachable recursion has
    # none to observe).

    @property
    def queue_to_higher(self):
        return self._queue_to_higher

    @queue_to_higher.setter
    def queue_to_higher(self, queue: asyncio.Queue):
        if self.__started:
            raise RuntimeError('AsyncLayerStack should not be changed after its tasks were started.')
        self._queue_to_higher = queue
        self.layers[0].queue_to_higher = queue

    @property
    def queue_from_higher(self):
        return self._queue_from_higher

    @queue_from_higher.setter
    def queue_from_higher(self, queue: asyncio.Queue):
        if self.__started:
            raise RuntimeError('AsyncLayerStack should not be changed after its tasks were started.')
        self._queue_from_higher = queue
        self.layers[0].queue_from_higher = queue

    @property
    def queue_to_lower(self):
        return self._queue_to_lower

    @queue_to_lower.setter
    def queue_to_lower(self, queue: asyncio.Queue):
        if self.__started:
            raise RuntimeError('AsyncLayerStack should not be changed after its tasks were started.')
        self._queue_to_lower = queue
        self.layers[len(self.layers) - 1].queue_to_lower = queue

    @property
    def queue_from_lower(self):
        return self._queue_from_lower

    @queue_from_lower.setter
    def queue_from_lower(self, queue: asyncio.Queue):
        if self.__started:
            raise RuntimeError('AsyncLayerStack should not be changed after its tasks were started.')
        self._queue_from_lower = queue
        self.layers[len(self.layers) - 1].queue_from_lower = queue

    def __insert(self, layer: AsyncLayerProcess, at: int):
        # Get the layers between which to insert the new layer
        layer_above = self.layers[at - 1] if at > 0 else None
        layer_below = self.layers[at] if at < len(self.layers) else None
        queues: List[asyncio.Queue] = []
        # If both layers exist, reuse the queues between them
        if layer_above is not None and layer_below is not None:
            queues.append(layer_above.queue_to_lower)
            queues.append(layer_above.queue_from_lower)
        # Create two new queues needed for connecting the new layer to the stack.
        for x in range(2):
            q = asyncio.Queue(maxsize=self.queue_size)
            self.queues.append(q)
            queues.append(q)
        # Set up queues to the layer above
        if layer_above is not None:
            q_up = queues.pop()
            q_down = queues.pop()
            layer_above.queue_to_lower = q_down
            layer_above.queue_from_lower = q_up
            layer.queue_to_higher = q_up
            layer.queue_from_higher = q_down
        # Set up queues to the layer below
        if layer_below is not None:
            q_up = queues.pop()
            q_down = queues.pop()
            layer.queue_to_lower = q_down
            layer.queue_from_lower = q_up
            layer_below.queue_to_higher = q_up
            layer_below.queue_from_higher = q_down
        # Insert the new layer at the wanted position
        self.layers.insert(at, layer)
        self.layers[0].queue_to_higher = self.queue_to_higher
        self.layers[0].queue_from_higher = self.queue_from_higher
        self.layers[len(self.layers) - 1].queue_to_lower = self.queue_to_lower
        self.layers[len(self.layers) - 1].queue_from_lower = self.queue_from_lower
