# Design ADRs — Modernization

Architecture Decision Records for the Python 3.14 + asyncio migration.

These record **why** the asyncio/Python 3.14 migration is shaped the way it
is, and **what not to do instead**. Read the relevant ones before changing
async behaviour.

## How an agent should use these

1. Before starting a phase, read every ADR listed for that phase.
2. Each ADR ends with **Rules for implementers** — treat those as binding.
3. Each ADR ends with **Verification** — a command or check proving the rule was
   followed.
4. If a task seems to contradict an ADR, **stop and report it**. Do not choose.

## Reading order by phase

| Phase | Read before starting |
|---|---|
| 0 — Baseline | ADR-001 |
| 1 — Python 3.14 | ADR-002 |
| 2 — Async foundations | ADR-003, ADR-004, ADR-005, ADR-006, ADR-007 |
| 3 — I/O boundary | ADR-008 (plus all of Phase 2's) |
| 4 — Remaining layers | ADR-003 addendum, ADR-009 |
| 5 — Node assembly | ADR-004 addendum (shared builders), ADR-006 addendum (AsyncMgmt), ADR-009 |
| 6 — Dead-code cleanup (dual runtime kept) | ADR-004 Phase 6 addendum, ADR-002 (retained), ADR-008 |
| 7 — Tests and CI | ADR-010 |

## Index

| ADR | Decision | Status |
|---|---|---|
| [001](ADR-001-baseline-first-migration.md) | Characterize behaviour before changing it | Accepted |
| [002](ADR-002-process-start-method.md) | Set the process start method explicitly to `fork` | Accepted |
| [003](ADR-003-handler-lifecycle.md) | Layer handlers become `async def` uniformly | Accepted |
| [004](ADR-004-async-layerstack.md) | `LayerStack` wires `asyncio.Queue` pairs; layers are tasks | Accepted |
| [005](ADR-005-queue-bounding.md) | Inter-layer queues are bounded | Accepted |
| [006](ADR-006-shutdown-cancellation.md) | Shutdown is cooperative cancellation | Accepted |
| [007](ADR-007-error-propagation.md) | Layer tasks are supervised; failures surface | Accepted |
| [008](ADR-008-baseinterface-contract.md) | Interfaces push inbound data; no file descriptors | Accepted |
| [009](ADR-009-cpu-bound-work.md) | CPU-bound work goes to an executor | Accepted |
| [010](ADR-010-async-test-strategy.md) | `pytest-asyncio` in strict mode, function-scoped loops | Accepted |

## Not covered here

- **CI configuration** — mechanics live in the task plan; there is no contested
  decision worth an ADR.
- **Phases 5–6 specifics** — node assembly and scaffolding removal follow from
  the ADRs above; no new decisions are anticipated. If one arises, add an ADR
  rather than improvising.

## Template

New ADRs follow the shape of the existing ones: Context → Options → Decision →
Consequences → **Rules for implementers** → **Verification**.

The last two sections are what make these usable by an agent rather than only
by a human reviewer. Do not omit them.
