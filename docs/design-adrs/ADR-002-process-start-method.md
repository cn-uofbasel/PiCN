# ADR-002: Set the process start method explicitly to `fork`

- **Status:** Accepted (temporary — retained while `runtime=sync` exists;
  original “retired by Phase 6” deferred; see ADR-004's 2026-08-04 Phase 6
  addendum)
- **Date:** 2026-08-03
- **Phase:** 1
- **Relates to:** `modernization.md` Phase 1

## Context

`multiprocessing` chooses a start method by platform. When this codebase was
written, macOS defaulted to `fork`. Modern Python defaults to `spawn` on macOS
and Windows.

Under `spawn`, the child process is a fresh interpreter: every object crossing
the boundary must be **pickled**. Layer objects cannot be.

Measured failure, `PiCN/ProgramLibs/ICNForwarder`:

```
TypeError: cannot pickle 'weakref.ReferenceType' object
  .../multiprocessing/reduction.py:60
```

with a follow-on failure because the process never started:

```
AttributeError: 'NoneType' object has no attribute 'terminate'
  .../multiprocessing/process.py:140
```

That second error is `stop_process()` calling `.terminate()` on a process that
does not exist.

**Verified:** forcing `fork` makes those same 4 tests pass.

Nothing in the codebase calls `set_start_method`, so behaviour depends entirely
on which platform it happens to run on.

## Options

### A — Make layer objects picklable

| Pros | Cons |
|---|---|
| Would work under `spawn`, the modern default | Requires removing weakrefs, sockets, and loggers from every layer's state |
| Portable to Windows | Large, invasive change to code we are about to replace anyway |
| | Effort is discarded entirely at Phase 6 |

### B — Set the start method explicitly to `fork`

| Pros | Cons |
|---|---|
| One small, documented change | `fork` is unavailable on Windows |
| Restores the suite immediately | Python warns: *"process is multi-threaded, use of fork() may lead to deadlocks in the child"* |
| Behaviour stops depending on platform defaults | Temporary — but that is the point |

### C — Leave the default and accept failing tests

| Pros | Cons |
|---|---|
| No change | Phase 1 cannot demonstrate compatibility; the baseline stays broken through every later phase |

## Decision

**Option B.** Set the start method explicitly to `fork` where the platform
supports it, leaving the default elsewhere.

This is explicitly a **bridge**, not a fix. The underlying problem is that the
architecture requires passing unpicklable objects between processes. The asyncio
migration removes process boundaries entirely, at which point this ADR is
retired.

Option A was rejected as effort spent on code scheduled for deletion.

## Consequences

- Phase 1 restores `ProgramLibs` tests without touching layer internals.
- The fork-related `DeprecationWarning` will appear in test output. Expected;
  do not suppress it — it is a standing reminder that this is temporary.
- Windows remains unsupported on the **sync** path; the async path supports it
  natively, so asyncio improves the situation rather than merely preserving it.
- **Retained, not removed.** The original plan retired this at Phase 6. Phase 6
  was narrowed and `runtime="sync"` remains supported, so
  `configure_start_method()` stays for as long as the sync path does. It is
  removed by the later phase that flips or drops the sync runtime — see
  ADR-004's 2026-08-04 Phase 6 addendum.

## Exact semantics of `set_start_method`

The behaviour must be stated precisely, because the obvious call is wrong in a
library context:

| Call | Behaviour |
|---|---|
| `set_start_method("fork")` | Raises `RuntimeError` if a start method was **already** set |
| `set_start_method("fork", force=True)` | **Silently overrides** an existing setting — no exception |
| `set_start_method("fork")` on a platform without `fork` | Raises `ValueError` |

`force=True` therefore does **not** need a `try/except RuntimeError` — it does
not raise for that case. More importantly, it would silently discard a
deliberate choice made by an embedding application. PiCN is a library; silently
mutating process-global state that an application configured is not acceptable.

**Required behaviour instead — inspect first, never override:**

```python
import multiprocessing, sys

def configure_start_method(logger=None) -> None:
    """Select 'fork' when nothing else has been chosen.

    Layer objects are not picklable (they hold weakrefs, sockets and loggers),
    so the 'spawn' default on macOS and Windows cannot start them. This is a
    bridge until the asyncio migration removes process boundaries entirely;
    see docs/design-adrs/ADR-002-process-start-method.md. Remove in Phase 6.
    """
    current = multiprocessing.get_start_method(allow_none=True)
    if current is not None:
        if current != "fork" and logger:
            logger.warning(
                "multiprocessing start method is already set to %r; leaving it "
                "unchanged. PiCN's process-based layers require 'fork' and may "
                "fail to start. See ADR-002.", current
            )
        return
    if "fork" not in multiprocessing.get_all_start_methods():
        if logger:
            logger.warning("'fork' unavailable on %s; using platform default. "
                           "Process-based layers may fail. See ADR-002.", sys.platform)
        return
    multiprocessing.set_start_method("fork")
```

`allow_none=True` is what makes "has anything been chosen yet?" answerable —
without it, `get_start_method()` sets and returns the default, and the question
can no longer be asked.

## Rules for implementers

1. **Do not use `force=True`.** Inspect with
   `get_start_method(allow_none=True)` and only set when the result is `None`.
2. If a start method is already set and it is not `fork`, **leave it alone** and
   log a warning explaining that process-based layers may fail. An application's
   deliberate configuration outranks ours.
3. Guard platform support with `get_all_start_methods()`; do not catch
   `ValueError` after the fact.
4. Add a comment stating **why**: layer objects are unpicklable, and this is
   removed when asyncio lands. Without it, a future reader assumes preference.
5. Calling this from `PiCN/Processes/__init__.py` applies it on import. That is
   a **process-global side effect of importing a library** — acceptable only
   because it is non-overriding, logged, and temporary. Document it in the
   module docstring.
6. **Do not** attempt to make any object picklable. No `__getstate__`,
   `__reduce__`, or weakref removal to "solve" this properly.
7. **Do not** suppress the fork/threads `DeprecationWarning`.
8. Do not touch `LayerProcess` or any layer as part of this task.

## Verification

```bash
.venv/bin/python -m pytest PiCN/ProgramLibs/ICNForwarder -q --timeout=90
```

Expect `4 passed`. These fail before this change and pass after.

No silent override anywhere:

```bash
grep -rn "force=True" PiCN/ --include=*.py
```

Expect **empty output**.

An existing setting is respected — this must print `spawn`, not `fork`:

```bash
.venv/bin/python -c "
import multiprocessing as mp
mp.set_start_method('spawn')
import PiCN.Processes
print(mp.get_start_method())
"
```
