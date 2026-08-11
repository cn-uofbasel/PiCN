# Modernization Plan: Python 3.14 and asyncio

**Status: complete.** Developed on branch `modernization/asyncio-python314`
prior to merge, phases 0–8. Kept as the rationale and audit trail for the
migration; see [`docs/design-adrs/`](design-adrs/README.md) for the resulting
design decisions and [`docs/baseline.md`](baseline.md) for the per-phase test
evidence.

This document was the task plan for bringing PiCN to current Python and
replacing its `multiprocessing`-per-layer execution model with `asyncio`. It
was written to be executed incrementally, by humans or AI coding agents, with a
verifiable state at the end of each phase.

Working conventions are in [`AGENTS.md`](../AGENTS.md).

---

## Why

### Current state (verified by reading the code, not assumed)

| Area | Finding |
|---|---|
| Target Python | `setup.py` shebang targets 3.6; `setup.cfg` configures `nose` |
| Test runner | `nose` is unmaintained and does not run on modern Python; it is not even declared as a dependency |
| Execution model | Every layer is a separate OS process, communicating over `multiprocessing.Queue` pairs |
| Run loops | **Three** variants in `LayerProcess`: `_run_poll`, `_run_select`, `_run_sleep` (Windows busy-wait at 0.3 s) |
| Loop selection | Partly decided by `in_unittest()`, which inspects the **call stack** for `"unittest"`/`"nose"` — unaware of `pytest` |
| Private API use | All run loops access `multiprocessing.Queue._reader` to obtain file descriptors |
| Link layer | `BasicLinkLayer` re-implements all three run loops to multiplex sockets alongside queues |
| Interface contract | `BaseInterface.file_descriptor` exists solely to support `select()`-based multiplexing |
| Serialisation | `PiCNProcess.__getstate__/__setstate__` drop the logger so layer objects can be pickled for `multiprocessing` |
| Shutdown | `stop_process()` uses `terminate()` plus two `sleep(0.1)` calls around queue teardown |
| Syntax rot | ~7+ files with invalid escape sequences; a small number of `is`/`is not` comparisons against literals |
| CI | None — no `.github/workflows/` |

### What asyncio removes

This migration is substantially a **deletion** exercise. Moving to asyncio makes
the following unnecessary:

- Three run-loop implementations collapse to one.
- `select`/`poll` handling and the Windows busy-wait fallback.
- The `multiprocessing.Queue._reader` private-API dependency.
- The `in_unittest()` call-stack inspection hack.
- `__getstate__`/`__setstate__` pickling support.
- `terminate()`-based shutdown and its timing-dependent sleeps.
- The 1024 file-descriptor ceiling imposed by `select`, which currently limits
  how large a simulation can be.

### Scope of the change (smaller than it first appears)

Layer business logic lives in `data_from_lower()` / `data_from_higher()` and is
mostly **synchronous computation over a queue interface**. The migration
primarily changes the *run loop* and the *queue type*, not the per-layer logic.

The genuine exceptions, which need real design work:

- **`BasicLinkLayer`** — multiplexes sockets and queues; must become
  event-loop-driven.
- **`UDP4Interface`** — blocking `socket.sendto`/`recvfrom` must become
  non-blocking (asyncio datagram transport/protocol, or `loop.sock_*`).
- **`BaseInterface`** — the `file_descriptor` contract changes shape.
- **NFN execution** — if any computation is CPU-bound, it must be dispatched to
  an executor rather than blocking the event loop.

---

## Known risks

| Risk | Detail | Mitigation |
|---|---|---|
| **Loss of true parallelism** | `multiprocessing` gave each layer its own GIL. asyncio is single-threaded concurrency | Identify CPU-bound work (NFN execution, crypto) and dispatch via `run_in_executor`. Measure before and after |
| **Hidden blocking calls** | Any blocking I/O or `time.sleep` inside a layer stalls the entire event loop, where previously it stalled only one process | Audit for blocking calls as part of each layer's migration; consider `asyncio` debug mode to surface slow callbacks |
| **Lost process isolation in tests** | Tests may implicitly rely on per-process state isolation | Phase 0 baseline plus per-test event-loop fixtures |
| **Timing-sensitive tests** | Tests tuned to `sleep`-based shutdown may become flaky or, conversely, expose real races | Convert to deterministic awaits rather than tuning sleep durations |
| **Behavioural drift during refactor** | Easy to "fix" protocol behaviour accidentally while restructuring | Characterization tests in Phase 0; behavioural changes require their own commits |

---

## Phases

Each phase ends in a working, testable state. Do not begin a phase before its
predecessor's exit criteria are met.

### Phase 0 — Baseline and safety net

**Goal:** know what currently works, before changing anything.

- [ ] Create a virtual environment and install the package plus `pytest`.
- [ ] Run the existing suite under `pytest` **without modifying any test**, and
      record the result: which tests pass, fail, error, hang, or are skipped.
- [ ] Commit that baseline as a file in the repo (e.g. `docs/baseline.md`) so
      later phases can be compared against it objectively.
- [ ] Identify tests that hang or bind fixed ports — these need attention before
      they can serve as a safety net.
- [ ] Write **characterization tests** for the layer contract itself: given data
      pushed to a layer's input queue, what appears on its output queues. These
      capture current behaviour and become the primary regression check for the
      architecture change.

**Exit criteria:** a recorded, reproducible baseline, and characterization tests
covering at least `ICNLayer`, `PacketEncodingLayer`, and `ChunkLayer`.

---

### Phase 1 — Python 3.14 compatibility (no architecture change)

**Goal:** run correctly on current Python while still using `multiprocessing`.
This isolates "does it work on 3.14" from "does asyncio work", so a failure in
Phase 2 cannot be confused with a version-compatibility problem.

- [ ] Add `pyproject.toml` declaring build metadata, an explicit supported
      Python range, and dev/test dependencies (`pytest`, `pytest-asyncio` for
      later phases).
- [ ] Move `opencv-python` to an optional extra; it is required only for
      data-offloading demos and does not build on current Python.
- [ ] Retire `setup.cfg`'s `[nosetests]` configuration in favour of pytest
      configuration.
- [ ] Fix invalid escape sequences (use raw strings or escape the backslash) —
      these are currently `SyntaxWarning` and are on track to become errors.
- [ ] Fix `is`/`is not` comparisons against `str`/`int` literals (use `==`/`!=`).
      Note these are latent bugs that work only by interning accident.
- [ ] Fix `in_unittest()` so it recognises `pytest`, **or** — preferable —
      replace the heuristic with an explicit configuration flag. The current
      call-stack inspection silently selects a different run loop under pytest.
- [ ] Set the `multiprocessing` start method **explicitly** rather than
      inheriting the platform default. Note macOS/Windows default to `spawn` on
      modern Python while this code was written under `fork` semantics; making
      this explicit keeps Phase 1 behaviour predictable.
- [ ] Re-run the suite; compare against the Phase 0 baseline.

**Exit criteria:** test results equal or better than baseline, on Python 3.14,
with no `SyntaxWarning` emitted during collection.

---

### Phase 2 — Async foundations

**Goal:** introduce the async execution model alongside the existing one,
without migrating any layer yet.

- [ ] Define the async layer base class: a single `async def run()` loop
      awaiting `asyncio.Queue` inputs from the adjacent layers, replacing all
      three `_run_*` variants.
- [ ] Decide and document the handler contract: do `data_from_lower` /
      `data_from_higher` become `async def`, or stay synchronous and get called
      from the async loop? (Recommendation: make them `async def` for
      uniformity, even where the body is synchronous — mixed contracts are a
      recurring source of confusion.)
- [ ] Define lifecycle: `start()` creates the task; `stop()` cancels it and
      awaits clean shutdown. No `terminate()`, no sleeps.
- [ ] Define the async `LayerStack` equivalent: wiring `asyncio.Queue` pairs
      between layers, preserving the existing `insert(on_top_of=/below_of=)`
      API shape.
- [ ] Unit-test the new base classes in isolation with dummy layers, including
      cancellation and clean shutdown.

**Exit criteria:** async base classes exist and are tested; no production layer
uses them yet; the existing stack still passes Phase 1 tests.

---

### Phase 3 — Migrate the I/O boundary

**Goal:** handle the hardest part first — the link layer and interfaces — since
this is where the `select()`-based design is most entrenched.

- [ ] Redesign the `BaseInterface` contract for asyncio. The
      `file_descriptor` property exists only for `select()` multiplexing;
      replace it with an async receive (e.g. `async def receive()`) or a
      datagram-protocol callback that pushes into a queue. Document the new
      contract explicitly — this is a public extension point.
- [ ] Port `UDP4Interface` to asyncio datagram transport
      (`loop.create_datagram_endpoint`), preserving broadcast support
      (`enable_broadcast`, `get_broadcast_address`).
- [ ] Port the simulation interface (`Interfaces/Simulation.py`), which is
      in-memory and should become straightforward under asyncio.
- [ ] Port `BasicLinkLayer`, deleting its three run-loop overrides — socket
      multiplexing becomes the event loop's job.
- [ ] Port `FaceIDTable`.
- [ ] Verify with characterization tests plus a two-node UDP round trip.

**Exit criteria:** two nodes exchange packets over real UDP using the async link
layer; no `select`/`poll` remains in link-layer code.

---

### Phase 4 — Migrate remaining layers

**Goal:** port the rest, one layer at a time, verifying each against its
characterization tests before moving on.

Suggested order — simplest first, so the pattern is established before the
complex cases:

- [ ] `PacketEncodingLayer` (pure transformation, no state)
- [ ] `ICNLayer` (Content Store, FIB, PIT — stateful but self-contained)
- [ ] `ChunkLayer`
- [ ] `RepositoryLayer` — audit for blocking file I/O; use a thread executor if
      needed
- [ ] `TimeoutPreventionLayer` — timer-driven; asyncio timers likely simplify it
- [ ] `NFNLayer` — audit the executor for CPU-bound work; dispatch via
      `run_in_executor` where appropriate
- [ ] `ThunkLayer`
- [ ] `RoutingLayer`, `AutoconfigLayer`

**Exit criteria:** every layer runs under the async model and passes its
characterization tests.

---

### Phase 5 — Node assembly and tooling

- [ ] Port `ProgramLibs` node types: `ICNForwarder`, `NFNForwarder`,
      `ICNDataRepository`, `ICNPushRepository`, `Fetch`.
- [ ] Port the `Mgmt` management interface.
- [ ] Port `starter/` CLI entry points; ensure they run an event loop correctly
      and shut down cleanly on `SIGINT`.
- [ ] Port `Simulations/`. Note these should now scale considerably further,
      since the `select()` file-descriptor ceiling is gone — worth verifying
      with a deliberately large scenario.

**Exit criteria:** `picn-relay`, `picn-fetch`, and the NFN forwarder work
end-to-end, and at least one simulation scenario runs.

---

### Phase 6 — Remove unused multiprocessing scaffolding (narrowed)

Phase 5 left a **dual runtime** (`runtime=sync|async`, default sync). Full
deletion of `LayerProcess` / sync `Mgmt` / Manager factories would break the
sync path. Phase 6 therefore **does not** retire sync; it deletes only what
is already unused, finishes deferred async ports that block honest greps,
and updates docs.

Locked decisions (2026-08-04):

1. Keep sync + async; delete dead code only.
2. Keep `SimulationBus` as an MP process (async nodes + sync bus); document
   an explicit exception in verification greps.
3. `Playground/` and DataOffloading / `NFNForwarderData` async: **port or
   delete** before Phase 6 greps are considered green.
4. Keep thin sync `Basic*Layer` wrappers (full scaffolding removal later).
5. Update `docs/architecture.md` and `docs/project_structure.md` as an
   exit criterion.

- [x] Inventory and ADR addendum: narrowed Phase 6 vs original modernization.md
- [x] Delete production-dead helpers (e.g. unused adapters) verified by grep
- [x] Port or delete DataOffloading + enable `NFNForwarderData` async
- [x] Port or delete `Playground/` MP layers
- [x] Document MP grep exceptions (sync ProgramLibs, SimulationBus, …)
- [x] Update architecture / project_structure docs for dual runtime

**Exit criteria:** dead code gone; Playground and DataOffloading resolved;
docs describe sync+async; greps match the documented exception list (not
“zero multiprocessing”). Full sync-path removal is deferred to a later phase.

---

### Phase 7 — Test infrastructure and CI

Deliberately separated from coverage work (Phase 8). CI should exist **before**
coverage expansion begins, so that new tests are themselves verified by the
pipeline and any regression surfaces immediately rather than at the end of an
open-ended testing effort.

- [x] Migrate remaining `nose`-style assertions to pytest idiom where they block
      progress; do not rewrite tests gratuitously.
- [x] Add `pytest-asyncio` fixtures and a consistent event-loop policy for tests.
- [x] Add GitHub Actions CI: run the suite on the supported Python range,
      ideally on Linux plus at least one other platform.
- [x] Record the final test state and compare against the Phase 0 baseline —
      this comparison is what demonstrates the migration preserved behaviour,
      and is the single most important artifact of the whole effort.

**Exit criteria:** CI green on the existing suite; the Phase 0 baseline
comparison documented and showing no unexplained regressions.

---

### Phase 8 — Coverage completion

Open-ended by nature, and safe to run continuously rather than as a gate.

- [x] Fill coverage gaps identified during migration. Likely candidates, based
      on the current structure:
  - [x] PIT expiry and timeout paths
  - [x] Content Store eviction behaviour
  - [x] FIB longest-prefix matching edge cases (empty names, single component,
    overlapping prefixes)
  - [x] Face/interface failure (post-close); reconnection **deferred** (no API)
  - [x] Chunking boundary conditions (exact-multiple sizes, single-byte payloads)
  - [x] Clean shutdown and cancellation under load (covered in Phase 2)
  - [x] Malformed packet handling at the encoding layer

**Exit criteria:** coverage meaningfully above the Phase 0 baseline, with the
gap list above addressed or explicitly deferred with reasons.

---

## Upstream contribution

This work is intended to be offerable upstream to
[cn-uofbasel/PiCN](https://github.com/cn-uofbasel/PiCN). To keep that possible:

- Keep commits scoped and individually reviewable.
- Keep public API shapes stable where practical; where they must change (notably
  `BaseInterface`), document the change and its rationale.
- Avoid mixing unrelated cleanups into architectural commits.
- Preserve the BSD-3-Clause licence and existing copyright headers.

Upstream's last activity was in 2024, so a contribution may or may not be
accepted; the phased structure means the work stands on its own regardless, and
individual phases could be offered as separate pull requests.
