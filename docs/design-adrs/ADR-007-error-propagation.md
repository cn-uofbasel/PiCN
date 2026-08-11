# ADR-007: Layer tasks are supervised; failures surface

- **Status:** Accepted
- **Date:** 2026-08-03
- **Phase:** 2
- **Relates to:** ADR-004, ADR-006

## Context

Today, an unhandled exception in a layer kills that layer's OS process. The node
degrades — traffic through that layer stops — but the failure is at least
*visible* as a dead process, and other layers keep running.

Under asyncio the failure mode is worse. An exception in an `asyncio.Task` is
stored on the task object and **only surfaces when someone awaits it**. If
nobody does, Python may emit `Task exception was never retrieved` at garbage
collection — possibly long after the fact, possibly not at all.

A layer can therefore die silently while the node appears healthy: queues fill
(ADR-005 bounds them, so producers block), and the symptom presents as a hang
somewhere unrelated to the actual fault.

This is a genuine regression in observability unless handled deliberately.

## Options

### A — Fire and forget

| Pros | Cons |
|---|---|
| No supervision code | A dead layer is invisible; debugging becomes guesswork |
| | Strictly worse than the current behaviour |

### B — Supervise every task; a layer failure fails the stack

| Pros | Cons |
|---|---|
| Failures surface immediately, with a traceback | A transient error takes the whole node down |
| Matches "fail loudly" — a broken forwarder should stop, not limp | Less resilient than per-process isolation was |
| Debugging points at the actual fault | |

### C — Supervise and restart the failed layer

| Pros | Cons |
|---|---|
| Most resilient | Restarting a stateful layer (PIT, CS, FIB) loses state and produces wrong behaviour, quietly |
| | Masks bugs during a migration whose purpose is to detect them |

## Decision

**Option B.** Every layer task is supervised. An unhandled exception in any
layer is logged with its traceback and fails the stack.

Option C was rejected for this stage specifically: restarting a layer that owns
forwarding state would produce a node that appears to work while behaving
incorrectly — the worst outcome during a migration meant to prove behaviour was
preserved. Resilience can be revisited once correctness is established.

## Consequences

- A bug in one layer stops the node, loudly, with a traceback. This is intended.
- `LayerStack` needs a supervision mechanism — `asyncio.TaskGroup` (3.11+) is
  the natural fit, since it cancels siblings when one task fails.
- Tests asserting on failure behaviour become possible, which they are not today.
- Long-running simulations become more brittle in exchange for being diagnosable.
  That is the right trade during migration.

## Rules for implementers

1. Never create a bare `asyncio.create_task(...)` and discard the handle. Either
   use `asyncio.TaskGroup`, or retain the reference and attach a done-callback
   that logs and propagates.
2. **Do not** wrap a layer's run loop in a blanket `except Exception: continue`.
   Swallowing errors to keep a layer alive is precisely the failure mode this
   ADR exists to prevent.
3. `asyncio.CancelledError` is **not** an error — it is normal shutdown
   (ADR-006). Handle it separately from genuine exceptions and re-raise it.
4. Log the full traceback, not `str(exception)`. A bare message loses the frame
   that identifies the fault.
5. Do not add restart or retry logic. If a layer fails, the stack fails.
6. Where an exception is genuinely expected and recoverable (a malformed packet,
   for instance), catch it **narrowly**, at the point it occurs, and log it.
   Never catch broadly at the loop level.

## Verification

No blanket exception swallowing in layer code:

```bash
grep -rn -B1 -A2 "except Exception" PiCN/Layers/ PiCN/Processes/ --include=*.py | grep -v test
```

Inspect each hit: it must either re-raise, or be a narrow, documented,
recoverable case. A bare `pass` or `continue` fails this ADR.

No orphaned tasks:

```bash
grep -rn "create_task" PiCN/ --include=*.py | grep -v test
```

Every hit must either be inside a `TaskGroup` or assign the result to a retained
reference.
