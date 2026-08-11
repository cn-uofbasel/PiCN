# ADR-001: Characterize behaviour before changing it

- **Status:** Accepted
- **Date:** 2026-08-03
- **Phase:** 0
- **Relates to:** `modernization.md` Phase 0

## Context

The migration replaces the execution model of every layer. The test suite is the
only mechanism that can tell us whether observable behaviour survived — but the
suite's own state on current Python is unknown, and parts of it predate the
platform it now runs on.

Measured on Python 3.14 / macOS / pytest 9.1.1 before any change:

| Scope | Result |
|---|---|
| Collection | 467 tests, 1 collection error (`numpy` absent) |
| `PiCN/Packets` + `PiCN/Layers/ICNLayer` | 80 passed |
| `PiCN/ProgramLibs/ICNForwarder` | 4 failed, 4 errors |

Some tests therefore fail **before** anyone touches the code. Without recording
that, every later failure is ambiguous: inherited, or newly introduced?

## Options

### A — Migrate, then fix whatever breaks

| Pros | Cons |
|---|---|
| Fastest start; no upfront work | "Did we break it?" becomes unanswerable |
| | Pre-existing failures get attributed to the migration, wasting effort |
| | Genuine regressions hide among inherited failures |

### B — Record a baseline first, then migrate

| Pros | Cons |
|---|---|
| Every later result is comparable against a known state | Delays the first code change |
| Regressions are identifiable rather than inferred | Baseline can go stale if phases run long |
| Characterization tests capture behaviour the suite never asserted | |

## Decision

**Option B.** Phase 0 records the current state and adds characterization tests.
No source file is modified during Phase 0.

Three runs are recorded, not one: collection, a full run under the platform
default start method, and a full run with the start method forced to `fork`. The
third isolates how much failure is caused by the process model rather than by
real breakage.

## Consequences

- Phase 0 produces only new files: `docs/baseline.md`, raw logs under
  `baseline/` (gitignored), and characterization tests.
- Every later phase ends with a comparison against this baseline.
- A test that passed at baseline and fails later is a **regression** and blocks
  the phase. A test that failed at baseline and still fails is not.

## Rules for implementers

1. **Do not modify any source file during Phase 0.** Adding files is allowed;
   editing existing ones is not.
2. **Do not fix failing tests during Phase 0.** A failing test is data.
3. Characterization tests assert **what the code does today**, not what it
   should do. Where behaviour looks wrong, still assert it and add a comment
   saying so.
4. Always run with `--timeout`. Some tests hang, and a hang with no timeout
   destroys the run rather than recording it.
5. Raw logs go in `baseline/` and are **not committed**. Only `docs/baseline.md`
   is.

## Verification

```bash
git diff --name-only HEAD~1 -- 'PiCN/**/*.py' | grep -v test_characterization
```

Expect **empty output** for the Phase 0 commit: no existing source file changed.
