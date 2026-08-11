# ADR-009: CPU-bound work goes to an executor

- **Status:** Accepted
- **Date:** 2026-08-03
- **Phase:** 4
- **Relates to:** ADR-003, ADR-004

## Context

Under multiprocessing, each layer had its own OS process and therefore its own
GIL. A layer performing heavy computation slowed only itself; other layers kept
forwarding.

Under asyncio (ADR-004) every layer shares one thread and one event loop. A
synchronous computation that runs for *n* milliseconds stalls **every** layer for
*n* milliseconds — including packet forwarding.

This is the single most significant behavioural regression the migration
introduces, and it is invisible until load is applied.

The computation layer is the obvious candidate: `PiCN/Layers/NFNLayer` contains
an executor and a parser, and executes named functions in a sandboxed Python
environment. Function execution time is arbitrary — it is user-supplied
computation.

Other candidates worth checking: content-store operations over large objects,
chunking, and any cryptographic or serialisation work over sizeable payloads.

## Options

### A — Run everything on the event loop

| Pros | Cons |
|---|---|
| Simplest; no executor management | A single slow computation stalls all forwarding |
| | Latency measurements become meaningless under load |
| | Reintroduces, in a new form, exactly the bottleneck the architecture avoids |

### B — Dispatch CPU-bound work to a thread executor

| Pros | Cons |
|---|---|
| Event loop stays responsive | Threads share the GIL, so CPU-bound Python does not truly parallelise |
| `loop.run_in_executor` is a one-line change at the call site | Helps latency, not throughput |
| Works for I/O-bound blocking calls too | |

### C — Dispatch to a process pool executor

| Pros | Cons |
|---|---|
| True parallelism; the GIL does not apply | Arguments and results must be picklable — the exact constraint that broke `spawn` (ADR-002) |
| | Reintroduces process management the migration removes |

## Decision

**Option B by default**, with C available where a specific workload proves both
CPU-bound and picklable.

The immediate objective is that **the event loop must not stall**. A thread
executor achieves that even without true parallelism, because the loop is free
to forward packets while the worker thread computes.

Option C is not adopted wholesale: the picklability constraint is what made
`spawn` fail, and reintroducing it as a default would recreate a solved problem.

## Consequences

- Named-function execution moves off the event loop. Its own latency may rise
  slightly; forwarding latency stops depending on it.
- An executor must be created and shut down with the stack (ADR-006).
- Thread-safety becomes a real concern for anything the executor touches — it no
  longer has the event loop's implicit single-threaded guarantee.
- Which work is actually CPU-bound must be **measured**, not assumed. See the
  rules.

## Executor ownership and lifecycle

**`LayerStack` owns exactly one executor.** Not layers, not `LayerProcess`, not
per-call.

Rationale: an executor is a pool of OS threads. One per layer would multiply
threads by layer count for no benefit, and a per-call executor would create and
destroy threads on the hot path. `LayerStack` already owns the queues and the
task lifecycle (ADR-004, ADR-006), so it is the natural owner.

Layers receive the executor by injection at construction or start. A layer must
never create its own.

### Startup and shutdown ordering

Ordering is not incidental — the wrong order either orphans work or fails
in-flight calls:

**Startup:** create the executor → start layer tasks.

**Shutdown** (extends ADR-006):

1. Cancel all layer tasks.
2. **Await** their completion (bounded by `SHUTDOWN_TIMEOUT`).
3. **Then** `executor.shutdown(wait=True)`.

Shutting the executor down *before* layers have stopped fails any in-flight
`run_in_executor` call with `RuntimeError: cannot schedule new futures after
shutdown` — surfacing as a spurious layer error during what should be a clean
stop. Shutting down with `wait=False` leaves worker threads running past process
teardown.

A layer awaiting an executor result when cancelled will raise `CancelledError`
at that `await`. The submitted function **still runs to completion** in its
thread — cancellation does not interrupt a thread. Executor functions must
therefore be safe to complete after their caller is gone, which is another
reason for the purity rule below.

### Thread-safety rules

Under multiprocessing, each layer had its own address space, so state was
isolated by construction. Under asyncio, layer state was protected by the event
loop's single-threaded execution. **An executor removes both guarantees**: a
worker thread runs concurrently with the loop.

The rule is therefore strict — **executor functions are pure with respect to
layer state**:

- Take everything needed as arguments.
- Return everything produced as a return value.
- Touch **no** layer attributes, no module-level mutable state, no shared
  collections.

Do not pass `self` or a layer object into the executor. If a function needs
layer data, pass a copy or an immutable view.

Where shared mutable state is genuinely unavoidable, it must be protected by an
explicit `threading.Lock`, and the call site must carry a comment justifying
why purity was not possible. Treat that as a last resort requiring review.

## Rules for implementers

1. Do not dispatch to an executor speculatively. **Measure first**: if a
   synchronous call can exceed ~10 ms, it belongs in an executor; otherwise leave
   it on the loop. Record the measurement in the commit message.
2. Dispatch form:
   ```python
   result = await loop.run_in_executor(self._executor, fn, *args)
   ```
3. **`LayerStack` owns the single executor.** Layers receive it by injection and
   never create one. No per-call or per-layer executors.
4. Shutdown order is fixed: cancel layers → await layers → `executor.shutdown(wait=True)`.
   Never shut the executor down first.
5. Executor functions are **pure with respect to layer state**: arguments in,
   return value out. Do not pass `self` or any layer object.
6. Anything running in the executor must not touch event-loop objects.
   Specifically forbidden: `asyncio.Queue`, any coroutine, `loop.*`.
7. Shared mutable state requires an explicit `threading.Lock` **and** a comment
   justifying why the function could not be pure.
8. **Do not** use `ProcessPoolExecutor` without first confirming the arguments
   and results are picklable — and record that check.
9. Do not "solve" a slow layer by adding sleeps or yielding with
   `await asyncio.sleep(0)`. That masks the stall rather than removing it.

## Verification

Blocking work is not called directly from a handler:

```bash
grep -rn "run_in_executor" PiCN/ --include=*.py | grep -v test
```

Each hit should correspond to a call site documented as measured CPU-bound.

The event loop is not starved — run the suite with asyncio debug mode, which
warns on callbacks exceeding 100 ms:

```bash
PYTHONASYNCIODEBUG=1 .venv/bin/python -m pytest PiCN/Layers/NFNLayer -q --timeout=120 2>&1 | grep -i "slow\|took"
```

Investigate every warning. Not all are faults, but each needs an explanation.

Exactly one executor is created, and only by `LayerStack`:

```bash
grep -rn "ThreadPoolExecutor\|ProcessPoolExecutor" PiCN/ --include=*.py | grep -v test
```

Expect hits **only** in `LayerStack`. Any occurrence inside a layer violates
ownership.

No layer object crosses into a worker thread:

```bash
grep -rn "run_in_executor" PiCN/ --include=*.py | grep -v test
```

Inspect each call: the function must not be a bound method of a layer, and `self`
must not appear in the arguments.

## Addendum (2026-08-04): a temporary, narrowly-scoped exception for Phase 3

Rule 3 above ("`LayerStack` owns exactly one executor") presumes a
`LayerStack` already exists to own it. During Phase 3
([ADR-008](ADR-008-baseinterface-contract.md)'s addendum), `BasicLinkLayer`'s
`AsyncRunStrategy` runs standalone inside its own forked process, wired into
the *old*, still-multiprocessing `LayerStack` -- there is no `AsyncLayerStack`
yet to own anything. Something still has to bridge the legacy
`multiprocessing.Queue` `from_higher` into the async engine without blocking
the event loop, which needs exactly the mechanism this ADR governs
(`loop.run_in_executor`).

**Exception: `AsyncRunStrategy` owns exactly one executor, for exactly this
bridge, for exactly as long as the layer runs under a transitional strategy
rather than a real `AsyncLayerStack`.**

- Not `BasicLinkLayer` itself -- the strategy object, so ownership moves
  cleanly with whichever run strategy is active.
- Not per-call, not per-interface. One executor, one purpose: draining
  `from_higher.get()` off the event loop.
- The function dispatched to it must still be pure per rule 5 above -- take
  the queue, return the item, touch nothing else.
- Startup/shutdown ordering still follows this ADR's ordering rules, just
  scoped to the strategy's own lifecycle instead of `LayerStack`'s: create the
  executor when the strategy starts, cancel the engine's tasks, await them,
  **then** `executor.shutdown(wait=True)`.

**This is deleted, not migrated, in Phase 5.** Once a ProgramLib's
`BasicLinkLayer` is wired into a real `AsyncLayerStack`, `from_higher` is a
real `asyncio.Queue` and the bridge -- and the executor it needed -- has
nothing left to do. The layer then receives `AsyncLayerStack`'s executor by
injection like every other layer, per rule 3, with no code path of its own
still creating one. Verify at that point with the original check above,
scoped to confirm `AsyncRunStrategy` is no longer among the hits.
