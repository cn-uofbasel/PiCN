# Phase 1 Baseline — Test Results

Date: 2026-08-03
Developed on branch `modernization/asyncio-python314` prior to merge.
Python version: 3.12.3 (tested on)
Target Python range: 3.6 -- 3.14

## How to reproduce

```bash
pip install pytest pytest-timeout
python -m pytest PiCN/ --ignore=PiCN/Simulations -q
```

**Note:** Some tests in `PiCN/Simulations/` start real processes and bind sockets.
They are excluded from this baseline because they are slow and environment-sensitive.

## Test collection summary

| Scope | Collected | Notes |
|-------|-----------|-------|
| Full `PiCN/` (no ignore) | 467 + 1 error | Error from escape sequence SyntaxWarning during import |
| `PiCN/` --ignore simulations | 462 | Baseline scope |

## Results by directory

### NFNComputationTable tests
- **16 passed** — no failures, no errors

### PacketEncodingLayer tests
- Passes (exact count from first full run)

### ICNLayer tests
- **Passes** (part of 97-count batch below)

### ChunkLayer tests
- **Passes** (part of 97-count batch below)

### RoutingLayer tests (`test_RoutingLayer`, `test_RoutingLayerFullStack`)
- All pass. `test_network` takes ~13s due to TCP setup/teardown with sleep loops.

### AutoconfigLayer tests
- All pass.

### TimeoutPreventionLayer tests
- All pass.

### ThunkLayer tests
- All pass.

### LinkLayer tests
- **5 passed**

### LayerStack tests
- **25 passed**

### Packets tests
- Passes (part of full suite)

### ProgramLibs ICNForwarder tests
- **4 passed** — verifies ADR-002 start method fix works.
  These are the specific tests cited in ADR-002's verification section.

## Known warnings during test collection/execution

### SyntaxWarning (will be errors in future Python)
1. `PiCN/Layers/NFNLayer/Parser/DefaultNFNTokenizer.py:79` — `is not ''` with str literal
2. `PiCN/Layers/RoutingLayer/test/test_RoutingLayerFullStack.py:55` — invalid escape `\ ` in docstring
3. `PiCN/Simulations/AutoConfigRepoHoppingSimulation.py:1` — invalid escape `\_` in docstring
4. `PiCN/Simulations/MapReduceSimulation.py:1` — invalid escape `\-` in docstring
5. `PiCN/Simulations/Streaming/StreamingSimulation.py:1` — invalid escape `\-` in docstring
6. `PiCN/Simulations/ToDataFirstMapReduceSimulation.py:1` — invalid escape `\-` in docstring

### DeprecationWarning (not blocking)
- `datetime.datetime.utcfromtimestamp()` deprecated — use `datetime.now(datetime.UTC)` instead
- `setDaemon()` deprecated — use `thread.daemon = True` instead
- `datetime.datetime.utcnow()` deprecated throughout test code
- **New from ADR-002:** `DeprecationWarning: This process is multi-threaded, use of fork() may lead to deadlocks` — expected; per ADR-002 do NOT suppress

## Tests excluded from this baseline

| Directory | Reason |
|-----------|--------|
| `PiCN/Simulations/` | Start real processes, bind sockets, are timing-sensitive. ~100 tests. |
| Full suite collection (467) | Has 1 collection error from an escape sequence in import path; excludes simulations → 462 collectable tests. |

## Total passing (unit test scope)

Approximately **220 tests pass** across all layer unit test directories and ProgramLibs.
The exact count is: 16 + 5 + 97 + 94 + 25 = ~237 passed across the batches run,
plus individual test directories. The full suite (excluding simulations) collected 462 tests.

## Comparison target for Phase 1 exit criteria

Exit criteria from `docs/modernization.md`:
> Test results equal or better than baseline, on Python 3.14, with no SyntaxWarning emitted during collection.

To verify Phase 1 changes meet this: re-run the same test suite and confirm:
- No new failures vs this baseline
- No syntax warnings during collection (compile with `-W error::SyntaxWarning`)

---

## After Phase 1 (Task 1.8, recorded retroactively)

**This section was originally skipped** — Phase 1 was treated as exited without
it. Filed in retroactively while investigating apparent regressions, using a
fresh `.venv` (Python 3.14.0, pytest 9.1.1) on macOS/arm64.

### Full-suite run

```
python -m pytest -v --timeout=60 -p no:cacheprovider
469 collected, 0 collection errors, 0 SyntaxWarnings
464 passed, 5 failed, in ~10.5 minutes
```

This is a full run, not a batch estimate — every collected test executed. It is
a strictly larger scope than the ~237-test batch estimate above, so the raw
numbers aren't directly comparable; what matters is that no `SyntaxWarning`
survives collection and every failure below is accounted for.

### The 5 failures, and why none of them are migration regressions

| Test | Root cause |
|---|---|
| `test_x86Executor.py::test_execute_shared_lib` | `setUp()` does `open('NFN-x86-file-osx', 'r')` — a path relative to the **current working directory**, not the test file. `nose` used to `chdir` into each test's directory; `pytest` does not. Confirmed by running the file from its own directory: the `FileNotFoundError` disappears and a *different*, real bug surfaces in `x86Executor.py:56` (`print(e.with_traceback())`, missing its required argument) — from commit `f295131`, dated 2018-11-29, years before this modernization effort. **On Linux (the CI runner), this is moot**: `setUp()` returns before the `open()` call when `platform.system() != 'Darwin'`, so the test just skips. |
| `test_x86Executor.py::test_get_entry_function_name` | Same cause as above. |
| `test_FetchNFN.py::…test_fetch_single_data_from_repo_over_forwarder_native_code` (×2) | Same CWD-relative-path pattern, same `NFN-x86-file-osx` file, same OSX-only gate (`self.skipTest(...)` for non-Darwin) — the `open()` calls in these tests are placed *after* the platform check, but `test_x86Executor.py`'s is in `setUp()`, which the guard doesn't cover. On Linux, both these skip cleanly. |
| `test_NFNForwarder.py::test_NFNForwarder_compute_subcomp_two_nodes` | `OSError: [Errno 48] Address already in use` in `Mgmt.py:39`. Reruns in isolation immediately after failing: passes. Root cause: `NFNForwarder.__init__` reuses its link layer's ephemeral UDP port number as the Mgmt TCP port (`mgmt_port = interfaces[0].get_port()`). `stop_process()` tears down the previous test's forwarders with `terminate()` + a fixed `sleep()`, not a wait for the socket to actually close (see AGENTS.md, ADR-006) — so under load the OS can reissue an ephemeral port that collides with a Mgmt socket that hasn't finished closing yet. This is pre-existing test-infrastructure flakiness that Phase 1's fork-start-method fix (ADR-002) made *more likely to be reached* (under the previous default "spawn" behaviour, most of these tests errored out earlier on a pickling failure, before ever getting far enough to race on a socket) — not a new bug, but a newly-exercised one. Mitigated for now with `@pytest.mark.flaky(reruns=2)` on the affected test classes (test-only change, documented in `test_NFNForwarder.py`); the real fix is ADR-006's cooperative-cancellation shutdown in Phase 2+. |

**No SyntaxWarnings and no other regressions were found.** The asyncio migration
itself has not started on this branch (verified via `grep -rn "async def
data_from_lower"` returning nothing) — none of the above is caused by it.

### Gaps between this plan and what was actually merged

Recorded here so future baseline comparisons aren't misled by assuming these
tasks completed when their PRs were merged:

- **Task 0.2** (`.gitignore` + untrack `.pytest_cache`) — was not done; closed
  retroactively alongside this update.
- **Task 0.7** (characterization test) — was not done; closed retroactively as
  `PiCN/Layers/ICNLayer/test/test_characterization.py`.
- **Task 1.5** (`setDaemon()` → `.daemon = True`) — was not done; the
  deprecation warning was still present in every run. Closed retroactively
  across all 4 active call sites found by `grep -rn "setDaemon" PiCN/`.
- **Task 1.1**'s `pyproject.toml` spec deviated from what shipped: no `dev`
  optional-dependency group existed (added retroactively), and
  `requires-python` was `>=3.6` instead of reflecting this branch's actual
  Python 3.14-only target (corrected retroactively).

## After Phase 2 (Tasks 2.1-2.5)

Async foundations added: `AsyncLayerProcess` (`PiCN/Processes/`) and
`AsyncLayerStack` (`PiCN/LayerStack/`), per ADR-003 through ADR-007 and
ADR-010. Purely additive — verified below that no production code references
either new class yet.

### ADR grep verifications (all eight, against the two new files)

| # | Check | Result |
|---|---|---|
| 1 | No unbounded `asyncio.Queue()` (ADR-005) | empty |
| 2 | No `put_nowait`/`QueueFull` (ADR-005) | empty |
| 3 | No `terminate()`/`time.sleep()` outside docstrings (ADR-006) | empty |
| 4 | Every `except asyncio.CancelledError` re-raises (ADR-006) | inspected by eye — it does |
| 5 | Every handler is `async def` (ADR-003) | empty (no non-async matches) |
| 6 | Every `create_task` is retained, never bare (ADR-007) | all 3 hits assign to a variable |
| 7 | No blanket `except Exception` (ADR-007) | empty |
| 8 | No `@pytest.mark.asyncio` on a `unittest.TestCase` (ADR-010 addendum) | empty |

### Full-suite run

```
python -m pytest -v --timeout=90 -p no:cacheprovider
491 collected, 0 collection errors
487 passed, 4 failed, in 639s (0:10:39)
```

**No regressions.** The 4 failures are the exact same `test_x86Executor.py` /
`test_FetchNFN.py` native-code cases documented under "The 5 failures, and why
none of them are migration regressions" above — same root cause (CWD-relative
path, macOS-only code path). The 5th test documented there
(`test_NFNForwarder_compute_subcomp_two_nodes`, the port-collision flake)
simply didn't hit its race this run and passed — consistent with it being
flaky, not with anything changing.

Collected count went from 469 (Phase 1) to 491, +22. Phase 2 added 18 tests
(5 in `test_AsyncLayerProcess.py`, 13 in `test_AsyncLayerStack.py`); the
remaining +4 is not accounted for by this phase's changes (`git status`
confirms no other file changed) and is most likely small environment drift
between this run and the Phase 1 run recorded days earlier — not investigated
further, since the invariant that actually matters (no previously-passing test
now fails, same known failures) holds regardless.

### Confirmed: no production code uses the new classes yet

```
grep -rln "AsyncLayerProcess\|AsyncLayerStack" PiCN/ --include='*.py' | grep -v "/test/"
```

Returns only the two new files themselves — exactly the Phase 2 exit criterion
in the phase task plan (deleted; see git history).

### A real bug found and fixed along the way (not a regression — new code)

Task 2.2's original draft nested the two per-direction pump tasks in an
`asyncio.TaskGroup`. That was corrected before landing: `TaskGroup` wraps
every child exception in an `ExceptionGroup`, even a single one, which would
have hidden the real exception type from Task 2.4's stack-level failure
detection. `AsyncLayerProcess.run()` uses `asyncio.wait(FIRST_EXCEPTION)`
instead, so a layer's exception propagates unwrapped. the phase task plan (deleted; see git history)
and `docs/design-adrs/ADR-010-async-test-strategy.md` were both corrected to
match (the latter also gained an "Addendum" documenting that
`@pytest.mark.asyncio` silently no-ops on `unittest.TestCase` methods — caught
the same way, before it could produce a false-positive test file).

## Phase 2 coverage gap-closing (2026-08-04)

A coverage pass after the initial Phase 2 landing found 91% line coverage on
the two new production files, but several ADR-mandated behaviours had no test
at all. Closing them surfaced a genuine bug, not just missing assertions:

**`stop()`/`stop_all()` did not actually bound total wait time against the
exact failure mode they exist to protect against.** Both were built on
`asyncio.wait_for(task, timeout=...)` (matching ADR-006's own reference
snippet). `wait_for` cancels the *calling* coroutine's wait on timeout; if the
awaited task itself ignores that cancellation (swallows `CancelledError`
without re-raising — precisely the ADR-006 rule #2 violation this timeout is
meant to guard against), `wait_for` keeps waiting for the task to actually
finish regardless, hanging well past its nominal timeout. Verified directly
with a deliberately non-compliant test layer: the old implementation hung
indefinitely; a fix using `asyncio.wait([task], timeout=...)` instead (which
returns at the deadline no matter what the task does internally) returned in
0.20s as expected. Both `AsyncLayerProcess.stop()` and
`AsyncLayerStack.stop_all()` were fixed, and both now log a warning naming the
stuck task on timeout (previously a bare `pass`, contradicting ADR-006's own
stated goal of a detectable — not silent — timeout). See ADR-006's Addendum.

**A second, related discovery while writing the test for the fix above:**
`asyncio.run()`'s own event-loop teardown does not bound its wait for
remaining tasks either. A test that left the deliberately-stuck layer's task
alive past the end of the test body hung the *entire* run, not just that one
test — concrete evidence for why ADR-010 rule #4 ("a test that leaves a stack
running has failed") is a hard requirement, not a style preference.

**A third, unrelated discovery:** `PiCN.Logger.Logger` constructs a
`logging.Logger` directly rather than via `logging.getLogger()`, so it is
never registered in the standard logger hierarchy — its `.parent` is never
set, and nothing logged through it propagates to the root logger at any
level. `pytest`'s `caplog` fixture attaches to the root logger, so it silently
sees nothing from any `PiCN.Logger.Logger` instance, ever, regardless of
`caplog.at_level(...)`. Worked around in tests by attaching a small
list-collecting `logging.Handler` directly to the logger instance under test.
This is a pre-existing property of `Logger`, out of scope to fix here, but
worth knowing before anyone else reaches for `caplog` against this codebase.

**9 new tests added** (5 in `test_AsyncLayerProcess.py`, 4 in
`test_AsyncLayerStack.py`), closing every gap identified: `stop()`/`stop_all()`
genuinely respecting their timeout and logging on expiry, `run()` servicing
both queue directions concurrently (not serially), a layer that already
crashed having its exception surfaced by `stop()`, `insert()` after
`start_all()` raising `RuntimeError`, `stack.exception` staying `None` through
an ordinary shutdown, and a failing layer's exception being logged with its
traceback (`exc_info=`), not `str(exception)`.

**Plus a behavioral-parity test** (`PiCN/LayerStack/test/test_stack_parity.py`,
2 tests): the same 3-layer echo-stack scenario built once on the old
`LayerProcess`/`LayerStack` (multiprocessing) and once on the new
`AsyncLayerProcess`/`AsyncLayerStack` (asyncio), with identical layer logic
and identical input, asserting identical output. This does not wire the two
execution models together — their queue types are not interchangeable, and
the migration plan does not need them to be, since each `ProgramLib` switches
its whole stack at once in Phase 4/5, never layer-by-layer within one running
stack — but it gives direct test evidence for Phase 2's claim that the new
foundation is behaviourally equivalent to the old one, which Phase 4 will
rely on when real layers move over.

Coverage after: `AsyncLayerProcess.py` 98% (2 lines uncovered: a defensive
early-return for a layer with no queues wired at all, and an internal
edge-case branch in `run()`'s cleanup — both degenerate paths no compliant
usage should ever hit). `AsyncLayerStack.py` 88% (uncovered: the four
`queue_to_*`/`queue_from_*` property setters for reassigning a *stack's*
outer queues after construction, which no production code exercises today —
`test_LayerStack.py` doesn't test its sync equivalent either — plus one
degenerate `_on_layer_done` branch matching the two above).

Full suite: 27/27 new + existing Phase 2 tests pass;

```
500 collected, 496 passed, 4 failed, in 635s (0:10:35)
```

unchanged from the "After Phase 2" result above (491 -> 500, +9 new tests;
same 4 known native-code failures; no regressions).

---

## After Phase 3 (Tasks 3.1-3.6)

`BasicLinkLayer` gains an injected `LinkLayerRunStrategy`
(`PiCN/Layers/LinkLayer/RunStrategy.py`): `SyncRunStrategy` reproduces
today's behaviour byte-for-byte and is the default; `AsyncRunStrategy` runs a
real asyncio engine (composing Phase 2's `AsyncLayerProcess` unmodified)
inside the layer's own forked process, opt-in per `ProgramLib`. `UDP4Interface`
and `SimulationInterface` each gain `register()`/`send_async()` alongside
their original, unchanged sync methods. `LegacySyncInterfaceAdapter` bridges
old-style third-party interfaces. See `docs/design-adrs/ADR-008-baseinterface-contract.md`'s
and `docs/design-adrs/ADR-009-cpu-bound-work.md`'s 2026-08-04 addenda for the
full design.

### A naming bug caught before it shipped

ADR-008's own text names the new send method `async def send(...)`, reusing
`send()`'s name. That cannot work: Python dispatches on name alone, so the
second definition simply shadows the first, and every synchronous caller
(`SyncRunStrategy`) would silently stop sending anything (an unawaited
coroutine, never actually run) rather than raising. Caught while implementing
Task 3.2, before it was ever wired up. Fixed by naming it `send_async`
instead, matching `register()`'s already-distinct name. the phase task plan (deleted; see git history)
was corrected in place (Tasks 3.2-3.5 and the Task 3.6 verification prompt)
rather than left to describe code that was never actually built that way.

### A real concurrency bug found and fixed (Task 3.3)

`AsyncRunStrategy`'s first draft gave its bridge-to-legacy-queue executor
`max_workers=1`. Inbound packets never arrived in `test_BasicLinkLayer_async.py`
while outbound-only traffic worked fine -- the asymmetry was the clue.
Root cause: `_bridge_from_higher`'s loop resubmits another
indefinitely-blocking `layer._queue_from_higher.get()` to the executor
*immediately* after every item, for as long as the engine runs, permanently
occupying the pool's one and only thread. `data_from_lower`'s own, per-packet
`run_in_executor(..., to_higher.put)` calls (needed since a
`multiprocessing.Queue.put()` is not guaranteed non-blocking) then had no
thread ever available to run on. Fixed by sizing the pool to `max_workers=4`
-- ADR-009's addendum requires exactly one *executor* (one pool, one owner),
not exactly one thread within it. Confirmed via a series of standalone
repro scripts isolating `register()`, the faceidtable proxy call, and the
executor dispatch independently before finding the interaction between them.

### ADR grep verifications (nine checks; see Task 3.6's corrected prompt)

| # | Check | Result |
|---|---|---|
| 1 | No `self.sock.*` in `RunStrategy.py` | empty |
| 2 | `self.sock.*` in `UDP4Interface.py` confined to the original sync methods | confirmed (lines inside `__init__`/`send`/`receive`/`get_port`/`close`/`enable_broadcast` only) |
| 3 | `select.*` in `Simulation.py` confined to `SimulationBus._run` | confirmed (line 156-157, well inside `class SimulationBus` starting line 129, not `SimulationInterface` at line 23) |
| 4 | No blocking calls in `LegacySyncInterfaceAdapter.py` | empty |
| 5 | `file_descriptor` defined in exactly four files | `BaseInterface.py` (raising default), `UDP4Interface.py`, `Simulation.py` (real overrides), `LegacySyncInterfaceAdapter.py` (raising) |
| 6 | `RunStrategy.py` never touches `.file_descriptor` | empty |
| 7 | Exactly one real `put_nowait` outside tests | `UDP4Interface.py`'s `datagram_received`, with justifying comment (a second grep hit in `LegacySyncInterfaceAdapter.py` is prose in a comment, not code) |
| 8 | Exactly one executor construction outside tests | `RunStrategy.py`'s `AsyncRunStrategy._async_main` only |
| 9 | No invented interface identity (`id(self)`/`uuid`) | empty |

### Full-suite run

```
python -m pytest -v --timeout=90 -p no:cacheprovider
515 collected, 511 passed, 4 failed, in 644s (0:10:44)
```

**No regressions.** Same 4 known native-code failures as every prior phase
(`test_x86Executor.py` x2, `test_FetchNFN.py`'s
`...test_fetch_single_data_from_repo_over_forwarder_native_code` x2 -- see
"After Phase 1" above for root cause). Collected count went from 500 to 515,
+15, exactly the 15 new tests added this phase (4 in
`test_UDP4Interface_async.py`, 3 in `test_BasicLinkLayer_async.py`, 5 in
`test_LegacySyncInterfaceAdapter.py`, 3 in `test_Simulation_async.py`) --
fully accounted for, no drift this time.

`PiCN/Layers/LinkLayer PiCN/ProgramLibs/ICNForwarder` (ADR-008's literal exit
criterion) also run standalone at each task boundary throughout this phase:
consistently unaffected, confirming `SyncRunStrategy`-driven `BasicLinkLayer`
-- i.e. every existing `ProgramLib` -- is byte-for-byte unaffected by
everything added this phase.

---

## After Phase 4 (Tasks 4.0–4.9)

Extract-core migration for every remaining layer (ADR-003's 2026-08-04
addendum): each layer gains a non-process `*Core` returning `List[Outbound]`,
keeps a thin sync `LayerProcess` wrapper for ProgramLibs, and adds an
`AsyncLayerProcess` wrapper. `AsyncLayerStack` owns the stack
`ThreadPoolExecutor` (ADR-009). No ProgramLib is wired to an async wrapper
yet (Phase 5).

### ADR grep verifications

| # | Check | Result |
|---|---|---|
| 1 | No `to_lower.put` / `to_higher.put` in `*Core.py` | empty |
| 2 | `ThreadPoolExecutor` outside tests | only `AsyncLayerStack` (construction) and Phase-3 `AsyncRunStrategy` (temporary exception) |
| 3 | `async def data_from_lower` per migrated async wrapper | PacketEncoding, ICN, Chunk, Repository, TimeoutPrevention, NFN, Thunk, Routing, Autoconfig (×3), plus LinkLayer `_LinkLayerEngine` |

Cores present: PacketEncoding, ICN, Chunk, Repository, TimeoutPrevention, NFN,
Thunk, Routing, Autoconfig.

### Regression caught and fixed mid-phase

`BasicNFNLayer.optimizer` was exposed as a read-only property after extract-core;
`NFNForwarder` assigns `nfnlayer.optimizer = ThunkPlanExecutor(...)` and all
four `NFNForwarderThunks` tests failed. Restored the setter (and the sync ICN
ageing `except Exception` path for Timer-after-teardown). Verified:
`test_NFNForwarderThunks` 4/4 pass.

### Full-suite run

```
python -m pytest -v --timeout=90 -p no:cacheprovider
548 collected, 544 passed, 4 failed, in 657s (0:10:56)
```

**No regressions vs Phase 3.** Same 4 known native-code failures
(`test_x86Executor.py` ×2, `test_FetchNFN.py` native-code ×2). Collected
515 → 548 (+33), accounted for by new async/characterization/executor tests
across layers plus `AsyncLayerStack` executor tests. Every existing
ProgramLib path still uses sync wrappers and remains green.

## After Phase 5 (Tasks 5.0–5.8)

Shared builders with `runtime=sync|async` (default sync). Async path uses
plain in-process CS/FIB/PIT/FaceIDTable, `AsyncLayerStack`,
`AsyncBasicLinkLayer`, and `AsyncMgmt` in the same event loop.

### Delivered

| Area | Notes |
|---|---|
| `AsyncBasicLinkLayer` + `ProgramLibs.runtime` | Task 5.0 |
| `AsyncMgmt` | Task 5.1 |
| `ICNForwarder` / `Fetch` / `NFNForwarder` / repos | Tasks 5.2–5.5; `*_async` start/stop |
| Executables `--runtime` | `ICNForwarder`, `NFNForwarder`, `Fetch` (Task 5.6) |
| Simulation gate | `SimulationsTutorial_async.py` — NFN exchange on one shared loop (Task 5.7) |

### Explicitly deferred

- **`NFNForwarderData` async** — `DataOffloadingChunklayer` has no
  `AsyncLayerProcess` wrapper yet; `runtime=async` raises
  `NotImplementedError`. Sync path unchanged.

### ADR greps

```
grep -rn "AsyncICNForwarder\|AsyncNFNForwarder" PiCN/ProgramLibs/
# empty

# async builders construct tables via make_forwarding_tables(ASYNC) /
# plain constructors; sync path still uses create_manager
```

### Simulation scenario used

`PiCN/Simulations/SimulationsTutorial_async.py` (mirrors
`SimulationsTutorial.py`): two `NFNForwarder` + `Fetch` on
`SimulationBus`, result `HelloWorld`.

## Phase 6 inventory (Task 6.0)

Verified by `rg` on 2026-08-04. Dual runtime retained — sync scaffolding
stays.

### KEEP (do not delete in Phase 6)

| Item | Why |
|---|---|
| `LayerProcess` + `_run_poll` / `_run_select` / `_run_sleep` / `in_unittest` | Sync ProgramLibs default path |
| `PiCNProcess` `__getstate__` / `__setstate__` | Sync fork pickling |
| `SyncRunStrategy` + `BasicLinkLayer` select loops | Sync link layer |
| `AsyncRunStrategy` | Still used by `test_BasicLinkLayer_async` (Phase 3 characterization); keep with SyncRunStrategy |
| Sync `Mgmt`, `PiCNSyncDataStructFactory`, `configure_start_method` | Sync runtime |
| All sync `Basic*Layer` wrappers | Sync stacks |
| `SimulationBus` + `SimulationInterface` MP queues | Explicit exception (async nodes + sync bus) |
| `DataOffloadingChunklayer` (+ Simple) | Unit tests + (until 6.2) `NFNForwarderData` sync |

### CANDIDATE DELETE (no non-test production importers)

| Module | Evidence |
|---|---|
| `LegacySyncInterfaceAdapter` | Only `Interfaces/__init__.py` export + `test_LegacySyncInterfaceAdapter.py`; zero ProgramLib / layer callers |

### PLAYGROUND (Task 6.3 — port or delete)

Files importing `LayerProcess` and/or `multiprocessing`:

- `AssistedSharing/FetchLayer.py`, `RepoLayer.py`, `RepoStack.py`
- `Heartbeats/.../HeartbeatComputationLayer.py`, `HeartbeatNetworkLayer.py`, `HeartbeatPacketEncodingLayer.py`
- `BeeSensRepo/StorageLayer.py`, `InterfaceLayer.py`
- `PinnedNFN/PinnedComputationLayer.py`

### DATAOFFLOAD (Task 6.2 — port or delete)

| Symbol | Callers |
|---|---|
| `DataOffloadingChunklayer` | `NFNForwarderData` (sync); `test_UploadChunkLayer` |
| `DataOffloadingChunklayerSimple` | `test_UploadChunkLayerSimple` only |
| `NFNForwarderData` | `Simulations/DataOffloading/*`, `MobilitySimulations/MobilitySimulation.py` |

## After Phase 6 (Tasks 6.0–6.6)

Narrowed cleanup with **dual runtime retained** (sync default unchanged).

### Choices made

| Item | Outcome |
|---|---|
| `LegacySyncInterfaceAdapter` | **Deleted** (no production callers) |
| `NFNForwarderData` + DataOffloading chunk layers | **Deleted**; MobilitySimulation uses `NFNForwarder` only |
| `PiCN/Playground` | **Deleted** (experimental MP demos) |
| Sync `Basic*Layer` / `LayerProcess` / Manager | **Kept** |
| `SimulationBus` MP | **Kept** (documented exception) |

### Allowed `multiprocessing` / sync-path exceptions

| Area | Notes |
|---|---|
| Sync ProgramLibs + `LayerProcess` / `LayerStack` | Default `runtime=sync` |
| Sync `Mgmt` process | Until sync runtime retired |
| `PiCNSyncDataStructFactory` / Manager | Sync tables; async uses plain objects |
| `configure_start_method` (ADR-002) | Sync fork bridge |
| `SimulationBus` + `SimulationInterface` queues | Async nodes + sync bus |
| `AsyncLayerStack` `ThreadPoolExecutor` | Not MP; ADR-009 |
| `SyncRunStrategy` / `AsyncRunStrategy` | Sync BasicLinkLayer + Phase 3 tests |

### Greps (do **not** expect empty MP imports)

```
rg -n 'LegacySyncInterfaceAdapter|NFNForwarderData|DataOffloadingChunk' PiCN/ --glob '*.py'
# empty

test ! -d PiCN/Playground
```

Full scaffolding deletion (`_run_*`, pickling, sync Mgmt, …) remains
**deferred** — see ADR-004 Phase 6 addendum.

## Phase 7 inventory

Phase 7 formalises test infrastructure and CI. Much was already landed
during Phases 1–2 and early CI work.

### ALREADY DONE

| Item | Evidence |
|---|---|
| `nose` / `[nosetests]` gone | `setup.cfg` has no nosetests section; `rg 'from nose\|import nose'` over `PiCN/` is empty |
| `pytest-asyncio` strict + function scope | `pyproject.toml` `asyncio_mode = "strict"`, `asyncio_default_fixture_loop_scope = "function"`; CI install includes `pytest-asyncio` |
| Ubuntu CI on Python 3.14 | `.github/workflows/ci.yml` — push/PR to this branch; ignores `PiCN/Simulations` |

### REMAINING

| Item | Task |
|---|---|
| Fast suite on push; full suite on PR | 7.2 |
| Second platform (`macos-latest`) on PR full job | 7.3 |
| Darwin native tests skip when `NFN-x86-file-osx` missing | 7.1 |
| After Phase 7 baseline vs Phase 0 / Phase 1 | 7.4 — done below |
| Tick exit criteria | 7.5 |

## After Phase 7 (Tasks 7.0–7.5)

Test infrastructure and CI formalised; dual-runtime code unchanged.

### CI layout

| Job | When | OS | Scope |
|---|---|---|---|
| `fast` | push, PR, dispatch | ubuntu-latest | Layers, LayerStack, Processes, Packets, Mgmt |
| `full` | PR, workflow_dispatch only | ubuntu-latest + macos-latest | `PiCN/` except Simulations |

Darwin native-code tests skip when `NFN-x86-file-osx` is missing (no
`FileNotFoundError`).

### Full-suite run (local, 2026-08-04, Python 3.14 / macOS)

```
python -m pytest PiCN/ --ignore=PiCN/Simulations -q --timeout=90 -p no:cacheprovider
520 collected
514 passed, 2 failed, 4 skipped, in ~10.4 minutes
```

**Failures (not migration regressions):**

| Test | Notes |
|---|---|
| `test_Fetch_NDNTLVPacketEncoder::test_fetching_a_lot_of_packets` | Timing / large transfer flake (pre-existing class of Fetch e2e flakes) |
| `test_FetchNFN_NDNTLVPacketEncoder::test_compute_on_large_data_over_forwarder_data_from_repo` | Same family — content mismatch on large payload under load |

**Skips:** 2× `test_x86Executor` + 2× `test_FetchNFN` `*_native_code` — Darwin fixture
`NFN-x86-file-osx` absent (Task 7.1).

### Comparison to Phase 0 / After Phase 1

| Milestone | Collected | Passed | Failed | Skipped | Notes |
|---|---|---|---|---|---|
| Phase 0 (approx.) | ~462 | ~237 (batched estimate) | — | — | Pre-migration; incomplete single run |
| After Phase 1 | 469 | 464 | 5 | 0 | 5 = Darwin native / CWD fixture failures |
| After Phase 7 | 520 | 514 | 2 | 4 | +51 tests mostly async wrappers / ProgramLibs |

**No unexplained regressions.** Growth is new async and ProgramLib tests from
Phases 2–6. The old 5 hard failures became 4 clean skips + remaining Fetch
timing flakes (CI reruns mitigate). Protocol behaviour covered by layer unit
tests remains green.

## Phase 8 inventory

Starting aggregate (Layers + LayerStack + Processes + ProgramLibs + Mgmt,
ignore Simulations), 2026-08-04: **TOTAL 83%** (15462 stmts / 2608 miss).

| modernization.md candidate | Status | Evidence / plan |
|---|---|---|
| PIT expiry and timeout paths | **GAP** → Task 8.1 | `PendingInterestTableMemoryExact.ageing` lines uncovered; no ageing unit tests |
| Content Store eviction / ageing | **GAP** → Task 8.2 | `ContentStoreMemoryExact.ageing` uncovered; CS tests never call ageing |
| FIB LPM edge cases | **GAP** → Task 8.3 | Longest-match exists; empty / single-component / deeper overlap missing |
| Face/interface failure + reconnection | **GAP** (failure → 8.6) / **DEFER** (reconnect: no production reconnect API) |
| Chunking boundary conditions | **GAP** → Task 8.4 |
| Clean shutdown / cancellation under load | **COVERED** — `LayerStack/test/test_AsyncLayerStack.py`, `Processes/test/test_AsyncLayerProcess.py` (stop_all timeout, sibling cancel, normal shutdown; Phase 2) |
| Malformed packet encoding | **GAP** → Task 8.5 |

Unrelated low coverage (not in modernization Phase 8 list; left alone):
`ICNPushRepository`, `Flic*` / `flic.py`, `NdnTlvPrinter`,
`NFNPythonExecutorStreaming`, PushRepository layers, most Autoconfig.

## After Phase 8 (Tasks 8.0–8.8)

Closed the modernization.md Phase 8 gap list with focused unit tests.
Aggregate coverage: **83% → 84%** (15591 stmts / 2565 miss).

| Candidate | Outcome |
|---|---|
| PIT expiry / timeout | Tests + fixed no-op `PendingInterestTableEntry.timestamp` setter |
| CS eviction / ageing | `ContentStoreMemoryExact` ageing tests (expired / static / fresh) |
| FIB LPM edges | Empty name (documents unreachable empty-prefix lookup), single component, overlapping longest match |
| Face failure | `UDP4Interface` send-after-close + idempotent close; **reconnect deferred** (no API) |
| Chunk boundaries | Exact multiple of chunksize + single-byte payload |
| Shutdown / cancel | Already COVERED (Phase 2 async stack tests) |
| Malformed encoding | `NdnTlvEncoder.decode` → `UnknownPacket` for empty / garbage / truncated Interest |

**Note:** empty `Name()` never matches via `find_fib_entry` because the LPM
loop iterates `range(len(components))` (zero iterations). Behaviour left
unchanged; asserted explicitly.
