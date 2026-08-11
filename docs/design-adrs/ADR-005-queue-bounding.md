# ADR-005: Inter-layer queues are bounded

- **Status:** Accepted
- **Date:** 2026-08-03
- **Phase:** 2
- **Relates to:** ADR-003, ADR-004

## Context

`multiprocessing.Queue` is effectively unbounded: it buffers in memory and
spills through a feeder thread. A slow layer therefore never applies
backpressure — the producer keeps accepting work and memory grows until
something fails.

`asyncio.Queue` defaults to `maxsize=0`, which is *also* unbounded. Porting
naively preserves the flaw while silently changing its character: under
multiprocessing the buffer was per-process; under asyncio everything shares one
heap.

This is easy to overlook precisely because nothing appears to break. It surfaces
as memory growth under sustained load — exactly the condition a benchmark
creates.

## Options

### A — Unbounded (`maxsize=0`), matching current behaviour

| Pros | Cons |
|---|---|
| Literal behavioural parity | Preserves a real defect |
| No producer ever blocks | Slow consumers cause unbounded memory growth |
| | Removes any signal that a layer is falling behind |

### B — Bounded with blocking `put`

| Pros | Cons |
|---|---|
| Backpressure propagates naturally toward the producer | A full queue can deadlock a cycle of layers |
| Memory is bounded by construction | Changes behaviour versus today |
| A slow layer becomes observable rather than invisible | Requires choosing a size |

### C — Bounded with drop-on-full

| Pros | Cons |
|---|---|
| Never blocks, never grows | Silently discards network packets — unacceptable for a forwarder under test |

## Decision

**Option B: bounded queues with awaiting `put`.** Default `maxsize` is a named
module-level constant, not a literal scattered through the code, and is
overridable per stack for tests and benchmarks.

Option C was rejected outright: silently dropping packets would corrupt every
measurement and every test in ways that look like bugs elsewhere.

## Consequences

- `await queue.put(...)` can now genuinely suspend. Handlers must be written
  expecting that (ADR-003 already makes them coroutines).
- A cycle of layers each blocked on a full queue is a **deadlock**. Layer graphs
  with cycles need care; if one is unavoidable, document it and give that edge a
  larger bound.
- Queue depth becomes a useful diagnostic: a persistently full queue identifies
  the slow layer directly.
- Benchmarks may need a larger bound than the default. That is a configuration
  change, not a code change.

## Choosing the bound

**There is no evidence behind any particular number yet, and none is invented
here.** The bound is a tunable constant with a documented method for settling
it, not a value presented as considered.

The constraint is two-sided:

- **Too small** — normal bursts block producers, adding latency that is an
  artifact of the setting rather than of the system.
- **Too large** — approaches unbounded: memory grows and a slow layer stays
  invisible, which is the defect this ADR exists to remove.

**Method for settling it, once the stack runs:**

1. Instrument `qsize()` per inter-layer queue during a representative run.
2. Record the **maximum observed depth** per queue under normal load.
3. Set the bound to roughly 2–4× that maximum: large enough to absorb bursts,
   small enough that a genuinely stuck layer hits the ceiling and becomes
   visible.
4. Record the measured maxima and the chosen value in the commit message, so the
   number has provenance.

Until that measurement exists, the starting value is explicitly provisional:

```python
# PROVISIONAL — not derived from measurement. See ADR-005 "Choosing the bound".
# Replace once per-queue depth has been measured under a representative run.
DEFAULT_QUEUE_SIZE = 128
```

A queue sitting persistently at its bound is a **diagnostic finding**, not a
sizing problem. Raising the bound to make the symptom disappear hides the slow
layer instead of identifying it.

## Rules for implementers

1. Define the default once, with the provisional comment above kept verbatim
   until a measurement replaces it. Do not scatter numeric literals.
2. **Do not silently raise the default** to make a test or benchmark pass. If a
   specific case needs more headroom, pass a larger size at construction and say
   why.
3. `LayerStack` accepts an optional queue size and applies it to every queue it
   creates.
4. Always `await queue.put(item)`. **Do not** use `put_nowait` to dodge
   blocking — that reintroduces unbounded growth or silent drops.
5. **Never** catch `asyncio.QueueFull` and discard the item. If you believe an
   item may be dropped, stop and report it.
6. Expose `qsize()` per queue for the measurement in "Choosing the bound" —
   without it the constant can never be settled with evidence.

## Verification

No unbounded queue construction:

```bash
grep -rn "asyncio.Queue()" PiCN/ --include=*.py | grep -v test
```

Expect **empty output** — every construction passes an explicit `maxsize`.

No silent drops:

```bash
grep -rn "put_nowait\|QueueFull" PiCN/ --include='*.py' | grep -v /test
```

Expect hits **only** in `UDP4Interface.datagram_received` — see the addendum
below. Anywhere else is a violation.

---

## Addendum (2026-08-04): one sanctioned `put_nowait` — inbound UDP datagrams

Rules 4 and 5 (always `await put`, never catch `QueueFull` and discard) assume
the producer is inside a coroutine and can suspend. That assumption fails at
exactly one place, discovered while implementing ADR-008's push model:

**`asyncio`'s datagram protocol callback `datagram_received()` is a plain
method, not a coroutine.** It cannot `await queue.put(...)`. The alternatives
were:

| Option | Why rejected / chosen |
|---|---|
| `await queue.put(...)` | **Impossible** — not a coroutine context |
| `asyncio.create_task(queue.put(...))` | Rejected: unbounded task creation under load is a worse failure than a dropped datagram, and orphans tasks (ADR-007) |
| `put_nowait` + drop on full, **with a warning log** | **Chosen** |

**Why dropping is acceptable here specifically, and nowhere else.** ADR-005
exists because a silently dropped item on an *inter-layer* queue hides a real
bug — the sender believed delivery happened. Inbound UDP has no such contract:
the datagram could equally have been lost in the network. Dropping under
backpressure is UDP behaving like UDP, not a swallowed error. The bounded queue
plus the warning still surfaces the pressure.

The drop is **logged at warning level** with the interface id and peer address,
so it is observable rather than silent — which is the part of rules 4/5 that
actually matters.

**This exception does not generalise.** It applies to inbound datagram delivery
from a transport callback. Any *inter-layer* queue, and any producer that is a
coroutine, remains bound by rules 4 and 5 as written. Cross-referenced from
ADR-008's 2026-08-04 addendum.
