# ADR-006: Shutdown is cooperative cancellation

- **Status:** Accepted
- **Date:** 2026-08-03
- **Phase:** 2
- **Relates to:** ADR-004, ADR-007

## Context

Current shutdown, in `LayerProcess.stop_process()`:

```python
self.process.terminate()
time.sleep(0.1)
# close and join each queue
time.sleep(0.1)
```

Three problems, all visible in that snippet:

1. `terminate()` sends `SIGTERM` — the layer gets no chance to finish in-flight
   work.
2. The two `sleep(0.1)` calls are timing guesses standing in for synchronisation.
3. If the process never started, `self.process` is `None` and `.terminate()`
   raises `AttributeError` — the observed cascade failure in ADR-002.

Under asyncio there is no process to signal. A task is stopped by cancellation,
which raises `asyncio.CancelledError` inside it at the next `await`.

## Options

### A — Cancel the task and move on

| Pros | Cons |
|---|---|
| Simple | Does not wait for the layer to finish; in-flight work vanishes |
| | Resources (sockets, files) may not be released before the process exits |

### B — Cancel, then await the task, with a timeout

| Pros | Cons |
|---|---|
| Layers get a chance to clean up | Slightly more code |
| Shutdown becomes deterministic instead of sleep-timed | A layer that swallows `CancelledError` will hang until the timeout |
| Failure to stop is detectable rather than silent | |

### C — A sentinel value on the queue

| Pros | Cons |
|---|---|
| No cancellation semantics needed | Does not interrupt a layer blocked anywhere other than that queue |
| | Every layer must handle the sentinel; missing one hangs shutdown |

## Decision

**Option B.** `stop()` cancels the layer's task, then awaits it with a bounded
timeout, treating `CancelledError` as the expected outcome.

No `terminate()`. No `sleep()` as a synchronisation device.

## Consequences

- Shutdown is deterministic: when `stop()` returns, the task has ended or the
  timeout expired and that is reported.
- Any layer holding a resource must release it in a `finally` block, since
  cancellation unwinds through `await` points.
- The `AttributeError` on unstarted layers disappears — `stop()` on a layer that
  never started is a no-op.
- Tests can start and stop stacks quickly and repeatedly, without sleep-tuning.

## Rules for implementers

1. `stop()` cancels the task, then awaits it:
   ```python
   task.cancel()
   try:
       await asyncio.wait_for(task, timeout=SHUTDOWN_TIMEOUT)
   except (asyncio.CancelledError, TimeoutError):
       pass
   ```
2. **Never swallow `CancelledError` inside a layer.** Catching it to "keep
   running" makes the layer unstoppable. If you must clean up, re-raise:
   ```python
   except asyncio.CancelledError:
       await self._cleanup()
       raise          # <- mandatory
   ```
   **Exception — awaiting a task you just cancelled yourself.** Rule 2 is about
   a layer swallowing cancellation *of its own run loop*. It does **not** apply
   when you cancel a child task you own and then await it to confirm it
   stopped:

   ```python
   async def stop(self, timeout: float = None) -> None:
       if self._ageing_task is not None:
           self._ageing_task.cancel()
           try:
               await self._ageing_task
           except asyncio.CancelledError:
               pass          # <- correct: we requested this cancellation
           self._ageing_task = None
       await super().stop(timeout=timeout)
   ```

   Re-raising here would propagate a cancellation **nobody asked `stop()` for**,
   turning an orderly teardown into a spurious `CancelledError` in the caller.
   The distinguishing question is *who requested the cancellation*: if it came
   from outside (your run loop was cancelled) you must re-raise; if you issued
   it yourself on a task you own, swallow it.

   All current `except asyncio.CancelledError: pass` sites in the codebase are
   this second case — verified 2026-08-04 across `AsyncBasicICNLayer`,
   `AsyncBasicRoutingLayer`, `AsyncBasicTimeoutPreventionLayer`,
   `AsyncAutoconfigRepoLayer`, and `AsyncAutoconfigClientLayer` (×2). Do not
   "fix" them.
3. Release resources in `finally`, not after the loop — cancellation may unwind
   before the loop's normal exit.
4. `stop()` on a layer that never started must be a **no-op**, not an error.
5. **Do not** call `time.sleep()` anywhere in shutdown. Do not add sleeps to make
   a flaky shutdown test pass; fix the synchronisation.
6. `SHUTDOWN_TIMEOUT` is a named constant, not a literal.

## Verification

No process-era shutdown primitives remain after Phase 6:

```bash
grep -rn "terminate()\|time.sleep" PiCN/Processes/ PiCN/LayerStack/ --include=*.py | grep -v test
```

Expect **empty output**.

No layer swallows cancellation **of its own run loop**:

```bash
grep -rn -B4 -A3 "except asyncio.CancelledError" PiCN/ --include='*.py' | grep -v /test
```

Classify each hit using rule 2's exception:

- Preceded by a self-issued `<task>.cancel()` then `await <task>` →
  **correct as `pass`**.
- Anywhere else, notably inside `run()` → **must contain `raise`**.

A `pass` with no preceding self-issued `cancel()` is the violation this ADR
exists to catch. A bare `grep ... | grep raise` cannot make this distinction —
the preceding lines are what decide it.

## Addendum (2026-08-04): the timeout branch must log, not just `pass`

Found while writing the test for `stop()`'s timeout path (Task 2.2 originally
shipped with no test exercising it at all): the reference snippet above lists
"failure to stop is detectable rather than silent" as a reason for choosing
Option B, but the snippet itself is `except (asyncio.CancelledError,
TimeoutError): pass` — a timeout is exactly as silent as the `CancelledError`
case it's grouped with. A caller awaiting `stop()` cannot distinguish a clean
stop from a timeout without separately polling the task.

**Rule, refining #1 above:** split the two cases. `CancelledError` (the
expected outcome) still passes silently. `TimeoutError` must log a warning
naming the layer and the timeout used, before returning — still without
raising, since `stop()`'s contract (never raise during teardown) is unchanged.
This is a logging addition only; it does not change `stop()`'s return value or
exception behaviour, so nothing that already calls `stop()` needs to change.

```python
try:
    await asyncio.wait_for(task, timeout=timeout)
except asyncio.CancelledError:
    pass
except TimeoutError:
    self.logger.warning(
        "%s did not stop within %.1fs of being cancelled -- it may be "
        "swallowing asyncio.CancelledError without re-raising it (rule #2).",
        self.logger.name, timeout,
    )
```

`AsyncLayerStack.stop_all()` follows the same split, logging which layer
task(s) specifically failed to stop.

**Added verification** — proving this path fires at all requires a
deliberately non-compliant test layer (one that swallows its first
cancellation), since no compliant layer should ever hit it:

```bash
python -m pytest PiCN/Processes/test/test_AsyncLayerProcess.py -k timeout -v
```

Expect a passing test that starts a stubborn layer, calls `stop()` with a
short timeout, and asserts the task is genuinely still running afterward
(proving the timeout — not a clean stop — occurred), then cleans it up with a
second, unhandled cancellation.

---

## Addendum (2026-08-04) — AsyncMgmt in the node event loop (Phase 5)

Sync `Mgmt` runs as a `multiprocessing.Process` with blocking `accept()` /
`recv()`, and `stop_process()` uses `terminate()` plus timing sleeps — the
exact pattern this ADR forbids.

### Decision

For the **async** ProgramLib runtime, port management into
`AsyncMgmt`: an asyncio TCP server (`asyncio.start_server` or equivalent)
on `127.0.0.1:port`, running as a supervised task in the **same** event
loop as `AsyncLayerStack`. Shutdown:

1. Cancel the Mgmt server task (and close the listening socket).
2. Await it bounded by `SHUTDOWN_TIMEOUT`.
3. Then `await stack.stop_all()` (which shuts the stack executor last —
   ADR-009).

Do **not** call `process.terminate()` or `time.sleep` on the async path.
The sync `Mgmt` class remains for the sync runtime until Phase 6.

HTTP request parsing and FIB/CS/PIT mutation semantics stay characterized —
do not change management wire format while changing the transport.
