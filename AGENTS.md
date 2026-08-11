# AGENTS.md — Working conventions for AI coding agents

Instructions for AI coding agents (and humans) contributing to this fork of
[PiCN](https://github.com/cn-uofbasel/PiCN). Read this before making changes.

## What this project is

PiCN is a modular Python implementation of Information-Centric Networking (ICN)
and Named Function Networking (NFN), originally from the Computer Networks Group
at the University of Basel. It provides a layered network stack — link layer,
packet encoding, ICN forwarding (Content Store, FIB, PIT), chunking,
repository, and NFN computation — that can be assembled into different node
types (forwarder, repository, NFN node).

## State of this codebase

PiCN has been through a **completed** modernization (originally developed on
branch `modernization/asyncio-python314` prior to merge): Python 3.14 support,
an `asyncio` runtime alongside the original multiprocessing-per-layer path, and
a `pytest` suite with CI.

- [`docs/design-adrs/`](docs/design-adrs/README.md) — the design decisions, each
  with binding rules and verification commands. **Read these before changing
  async behaviour.**
- [`docs/architecture.md`](docs/architecture.md) — the dual runtime
- [`docs/modernization.md`](docs/modernization.md) ·
  [`docs/baseline.md`](docs/baseline.md) — historical rationale and the
  per-phase test evidence

**The runtime is dual.** `runtime="sync"` (the default) uses `LayerProcess` +
`multiprocessing.Queue`; `runtime="async"` uses `AsyncLayerProcess` +
`asyncio.Queue`. Both are supported. The sync path is **not** dead code — do
not delete it, and do not assume async-only when editing shared modules.

Changes here are intended to be **contributable upstream**. Keep commits
focused, keep the public API stable where possible, and document behavioural
changes explicitly.

## Ground rules

**Do not change network behaviour while changing architecture.** Packet
formats, forwarding semantics, and PIT/FIB/CS logic must stay observably
identical. If a behavioural change appears necessary, stop and flag it rather
than absorbing it into a refactor commit.

**Protocol logic lives in `*LayerCore.py`, not in the wrappers.** Each layer is
a shared core plus a thin sync wrapper (`Basic*Layer`) and async wrapper
(`AsyncBasic*Layer`). Put behaviour in the core so the two runtimes cannot
drift; put only scheduling in the wrappers.

**One layer at a time.** Migrate and verify layers individually; do not attempt
a whole-stack change in a single commit.

**Do not reach into private APIs on the async path.** The retained sync loops
still use `multiprocessing.Queue._reader`; new async code must not introduce
equivalent dependencies (ADR-004).

**Verify against the ADRs.** Each ADR ends with a runnable verification command.
Run the relevant ones before opening a PR.

## Repository layout

```
PiCN/
  LayerStack/      # LayerStack: assembles layers, wires queues between them
  Processes/       # PiCNProcess / LayerProcess: per-layer execution model
  Layers/          # One subpackage per layer, each with its own test/ folder
    LinkLayer/         # Faces/interfaces (UDP, simulation), FaceIDTable
    PacketEncodingLayer/   # Wire format <-> Python objects (NDN TLV)
    ICNLayer/          # Content Store, FIB, PIT, forwarding logic
    ChunkLayer/        # Segmentation of large objects
    RepositoryLayer/   # Persistent content storage
    NFNLayer/          # Named Function Networking: parser, optimizer, executor
    ThunkLayer/        # Execution state management
    RoutingLayer/, AutoconfigLayer/, TimeoutPreventionLayer/
  ProgramLibs/     # Node types assembled from layers (ICNForwarder, NFNForwarder, ...)
  Packets/         # Packet types (Interest, Content, Nack) and names
  Mgmt/            # Management interface
  Simulations/     # Multi-node simulation scenarios
docs/              # Project documentation
starter/           # CLI entry points (picn-relay, picn-fetch, ...)
```

## Development setup

Python 3.14. Dependencies are declared in `pyproject.toml`; PiCN has **no
required runtime dependencies**.

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

`opencv-python` is an optional extra (`pip install -e ".[opencv]"`), needed only
for unrelated demos.

## Running tests

```bash
python -m pytest PiCN/ --ignore=PiCN/Simulations --timeout=90
```

Run a single layer's tests while working on it:

```bash
python -m pytest PiCN/Layers/ICNLayer/
```

Notes:

- **Always pass `--timeout`.** Some tests bind sockets and start processes; a
  hang otherwise blocks the whole run.
- `PiCN/Simulations` is excluded from CI (slow, environment-sensitive). Run it
  deliberately, not by default.
- Async tests use `pytest-asyncio` in **strict** mode — every async test needs
  `@pytest.mark.asyncio`, and must **not** live on a `unittest.TestCase`
  subclass (it would silently no-op). See ADR-010.

## Code conventions

- **Type hints**: partially present today (e.g. `LayerStack.py`,
  `BasicICNLayer.py`). Add them to code you touch; do not embark on a
  repo-wide typing sweep as part of an unrelated change.
- **Docstrings**: existing style is Sphinx-flavoured with `:param:` / `:return:`
  / `:raises:`. Match it in the modules you edit.
- **Comments**: explain *why*, not *what*. Non-obvious invariants — especially
  ordering or concurrency assumptions surfaced by this migration — are worth a
  line; restating the code is not.
- **Commit scope**: one concern per commit. "Migrate ICNLayer to asyncio" and
  "fix escape sequences repo-wide" are separate commits.

## Things that will surprise you

Real properties of the codebase, verified by reading it. Most are consequences
of the **sync path being retained** — they are not leftovers to clean up.

**Sync path (still live, still supported):**

- `LayerProcess` has **three** run-loop implementations — `_run_poll`
  (`select.poll`), `_run_select` (`select.select`), and `_run_sleep` (a 0.3 s
  busy-wait for Windows). All three remain because `runtime="sync"` is the
  default.
- Which loop runs is decided partly by `in_unittest()`, which **inspects the
  call stack**. It now recognises `pytest` (Phase 1) but is still a heuristic.
- `LayerProcess`, `BasicLinkLayer`, and `Interfaces/Simulation.py` reach into
  `multiprocessing.Queue._reader`. This is the documented exception list in
  ADR-004 — the async path is clean and must stay so.
- `PiCNProcess` still implements `__getstate__`/`__setstate__` for pickling;
  `multiprocessing` needs it. `configure_start_method()` in
  `PiCN/Processes/__init__.py` sets `fork` **at import time**, but only when
  nothing else has been chosen — it never overrides an application's setting
  (ADR-002).

**Async path:**

- Inter-layer queues are **bounded**; `await queue.put(...)` can genuinely
  suspend (ADR-005).
- `UDP4Interface.datagram_received` is the **one** sanctioned `put_nowait` +
  drop, because a transport callback cannot `await`. It logs on drop
  (ADR-005 addendum).
- `except asyncio.CancelledError: pass` appears in several `stop()` methods and
  is **correct** there — those await a child task the layer itself just
  cancelled. Swallowing cancellation of a layer's own `run()` loop is not
  (ADR-006 rule 2).
- `AsyncLayerStack` owns the **single** `ThreadPoolExecutor`; layers receive it
  by injection (ADR-009).
- An async test defined on a `unittest.TestCase` subclass **silently passes
  without running** (ADR-010 addendum).
