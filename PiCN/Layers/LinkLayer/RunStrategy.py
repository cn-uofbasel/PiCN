"""Run strategies for BasicLinkLayer.

See docs/design-adrs/ADR-008-baseinterface-contract.md's 2026-08-04 addendum
for the full rationale. In short: BasicLinkLayer is production code every
ProgramLib already depends on, so it cannot simply be rewritten in place the
way Phase 2's purely-additive AsyncLayerProcess/AsyncLayerStack were. Instead
BasicLinkLayer takes an injected LinkLayerRunStrategy deciding what actually
happens inside its dedicated forked process:

- SyncRunStrategy reproduces today's LayerProcess.start_process() exactly.
  It is the default, so every existing ProgramLib is completely unaffected.
- AsyncRunStrategy runs a real asyncio engine instead, opt-in per ProgramLib.

Both live in this one module because they implement the same seam and are
meant to be read side by side.

Phase 5 promotes the engine to AsyncBasicLinkLayer for use inside
AsyncLayerStack (no fork). AsyncRunStrategy reuses that class with a
multiprocessing-Queue bridge for the Phase-3 opt-in path.
"""

import abc
import asyncio
import concurrent.futures
import multiprocessing

from PiCN.LayerStack.AsyncLayerStack import DEFAULT_QUEUE_SIZE


class LinkLayerRunStrategy(abc.ABC):
    """Decides what BasicLinkLayer.start_process() actually does.

    Injected at BasicLinkLayer construction rather than hardcoded, so a
    ProgramLib can opt into the asyncio-based engine (Task 3.3) without every
    other ProgramLib -- or BasicLinkLayer's public shape -- changing at all.
    """

    @abc.abstractmethod
    def start(self, layer: "BasicLinkLayer") -> None:
        """Start layer's process. Must set layer.process, matching
        PiCNProcess's existing contract (stop_process() calls
        layer.process.terminate())."""


class SyncRunStrategy(LinkLayerRunStrategy):
    """Today's behaviour, extracted verbatim from BasicLinkLayer's inherited
    LayerProcess.start_process() -- select()/poll() multiplexing the
    interfaces' file descriptors alongside queue_from_higher, exactly as
    before this refactor. Zero behavioural change (ADR-008).
    """

    def start(self, layer: "BasicLinkLayer") -> None:
        layer.process = multiprocessing.Process(target=layer._run, args=[
            layer._queue_from_lower, layer._queue_from_higher,
            layer._queue_to_lower, layer._queue_to_higher])
        layer.process.daemon = True
        layer.process.start()


class AsyncRunStrategy(LinkLayerRunStrategy):
    """Runs BasicLinkLayer's logic as real asyncio code (loop.
    create_datagram_endpoint via the interfaces, no select()/file_descriptor
    multiplexing) inside its own forked process. Opt-in per ProgramLib --
    see ADR-008's 2026-08-04 addendum.

    Phase 5: delegates to AsyncBasicLinkLayer. stop_process() is NOT
    overridden per strategy (BasicLinkLayer.stop_process() calls
    self.process.terminate()). Nothing here runs a graceful async shutdown
    path in that case -- the try/finally below exists to surface a layer
    crash loudly instead of hanging silently while the process is still
    alive, not to handle stop_process()'s termination path.
    """

    def start(self, layer: "BasicLinkLayer") -> None:
        layer.process = multiprocessing.Process(target=self._entrypoint, args=[layer])
        layer.process.daemon = True
        layer.process.start()

    def _entrypoint(self, layer: "BasicLinkLayer") -> None:
        """Runs inside the freshly-forked child process."""
        asyncio.run(self._async_main(layer))

    async def _async_main(self, layer: "BasicLinkLayer") -> None:
        # Exactly one executor (one pool, one owner -- ADR-009's 2026-08-04
        # addendum does not mandate exactly one THREAD), created at start,
        # not at construction (ADR-009's ordering rule). max_workers must be
        # >1: _bridge_from_higher below occupies one worker PERMANENTLY --
        # it resubmits another indefinitely-blocking
        # layer._queue_from_higher.get() immediately after every item, for
        # as long as this engine runs -- so a pool of exactly 1 would starve
        # data_from_lower's own, per-packet run_in_executor(..., to_higher.put)
        # calls forever. Found by observing inbound packets never arriving
        # despite register() and the queue plumbing both working in
        # isolation: outbound-only traffic (which does not need the
        # executor at all -- send_async() calls the transport directly)
        # worked fine, which is what pointed at the shared pool.
        from PiCN.Layers.LinkLayer.AsyncBasicLinkLayer import AsyncBasicLinkLayer

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        engine = AsyncBasicLinkLayer(
            layer.interfaces, layer.faceidtable, log_level=layer.logger.level,
        )
        engine.executor = executor
        engine.queue_from_lower = asyncio.Queue(maxsize=DEFAULT_QUEUE_SIZE)
        engine.queue_from_higher = asyncio.Queue(maxsize=DEFAULT_QUEUE_SIZE)
        engine.queue_to_higher = layer._queue_to_higher
        engine.queue_to_lower = None

        # register is performed inside AsyncBasicLinkLayer.run()

        async def _bridge_from_higher() -> None:
            loop = asyncio.get_running_loop()
            while True:
                item = await loop.run_in_executor(executor, layer._queue_from_higher.get)
                await engine.queue_from_higher.put(item)

        bridge_task = asyncio.create_task(
            _bridge_from_higher(), name="LinkLayer-from_higher-bridge")
        engine_task = engine.start()
        tasks = [bridge_task, engine_task]

        try:
            done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            for t in done:
                if t.cancelled():
                    continue
                exc = t.exception()
                if exc is not None:
                    raise exc
        finally:
            # Ordering per ADR-009: cancel -> await -> shut the executor
            # down, never the other way around. Cancelling an already-done
            # task is a harmless no-op, so this runs unconditionally.
            for t in tasks:
                t.cancel()
            await asyncio.wait(tasks)
            executor.shutdown(wait=True)
