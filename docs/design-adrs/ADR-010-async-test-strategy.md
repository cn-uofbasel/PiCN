# ADR-010: `pytest-asyncio` in strict mode, function-scoped event loops

- **Status:** Accepted
- **Date:** 2026-08-03
- **Phase:** 2 (adopted) / 7 (completed)
- **Relates to:** ADR-003, ADR-006, ADR-007

## Context

The existing suite is `unittest`-style and synchronous, written for `nose`
(unmaintained) and run under `pytest`. Measured state on Python 3.14:
**467 tests collect**; `PiCN/Packets` and `PiCN/Layers/ICNLayer` give **80
passes**.

Once handlers become coroutines (ADR-003), tests calling them directly must
await them, which needs an event loop per test. Several decisions follow, and
they are worth making once rather than per file:

- Which plugin, and in which mode.
- Event-loop scope: shared across a module, or fresh per test.
- Whether existing synchronous tests must change.

Getting loop scope wrong produces the worst kind of test failure: order-dependent
and intermittent.

## Options

### Event-loop scope

#### A — Session or module scoped

| Pros | Cons |
|---|---|
| Faster; one loop creation | State leaks between tests — a task left running in one test affects the next |
| | Failures become order-dependent and hard to reproduce |

#### B — Function scoped (fresh loop per test)

| Pros | Cons |
|---|---|
| Complete isolation; no leakage | Slightly slower |
| A leaked task fails its own test, not an unrelated one | |
| Failures reproduce in isolation | |

### Plugin mode

#### `asyncio_mode = auto` — coroutine tests run automatically

| Pros | Cons |
|---|---|
| No decorators needed | Silently changes how *every* collected coroutine is treated |
| | A test that should have been marked is run anyway, hiding the omission |

#### `asyncio_mode = strict` — explicit `@pytest.mark.asyncio`

| Pros | Cons |
|---|---|
| Async tests are visibly marked | One decorator per async test |
| A missing mark fails loudly instead of silently passing | |

## Decision

**`pytest-asyncio` in `strict` mode, with function-scoped event loops.**

Both choices favour explicitness and isolation over speed. In a migration whose
entire purpose is proving behaviour was preserved, a test suite that produces
order-dependent results is worse than a slower one.

Existing synchronous tests are **not** converted wholesale. They are updated only
where the code they exercise becomes async.

## Consequences

- `pyproject.toml` carries `asyncio_mode = "strict"` and the loop-scope setting.
- Every async test needs `@pytest.mark.asyncio`.
- A test leaking a running task fails that test, which is the desired signal.
- Shutdown behaviour (ADR-006) becomes directly testable: cancel a stack and
  assert it stopped within the timeout.
- Supervision (ADR-007) becomes testable: inject a failing layer and assert the
  stack surfaces the exception.

## Rules for implementers

1. Configure once, in `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "strict"
   asyncio_default_fixture_loop_scope = "function"
   ```
   Do not override scope in individual test files.
2. Mark every async test with `@pytest.mark.asyncio`. Do not switch to `auto`
   mode to avoid the decorator.
3. **Do not convert a passing synchronous test to async** unless the code it
   exercises became async. Gratuitous conversion loses baseline comparability
   (ADR-001).
4. Always start and stop stacks within the test. A test that leaves a stack
   running has failed even if its assertions passed.
5. Use `--timeout` on every run. An async test that hangs otherwise blocks the
   entire suite.
6. Do not use `time.sleep` in tests. Await the condition, or use
   `asyncio.wait_for`. Sleep-tuned tests are the flakiness this ADR exists to
   prevent.
7. Prefer asserting on observable output — what appears on a queue — over
   inspecting layer internals. Internals change during migration; the contract
   should not.

## Verification

Configuration is present and strict:

```bash
grep -A2 "asyncio_mode" pyproject.toml
```

No sleep-based synchronisation in tests:

```bash
grep -rn "time.sleep" PiCN/ --include=test_*.py
```

Expect **empty output** for newly written tests. Pre-existing occurrences are
recorded in the baseline and removed as their layers are ported.

Suite is order-independent — run it shuffled and compare against the baseline:

```bash
.venv/bin/pip install pytest-randomly
.venv/bin/python -m pytest PiCN/ -q --timeout=60
```

Counts must match the ordered run. A difference means shared state between
tests.

## Addendum (2026-08-04): `pytest-asyncio` does not run on `unittest.TestCase`

Discovered while implementing Task 2.2, not anticipated when this ADR was
written: `@pytest.mark.asyncio` has no effect on a coroutine method defined on
a `unittest.TestCase` subclass. Pytest hands `unittest.TestCase` tests to
`unittest`'s own test-running protocol, which pytest-asyncio's collection
hooks never see. `unittest` then calls the async `test_*` method like any
other, gets back a coroutine object, discards it, and reports the test as
**passed** — the body never ran.

This is strictly worse than the `auto`-mode failure mode this ADR rejected in
"Options": a missing mark there at least *runs* the coroutine (just without
pytest-asyncio's fixture support), whereas this silently no-ops the entire
test. It was caught only because the assertions inside were checked by eye
against a `RuntimeWarning: coroutine ... was never awaited` in the output —
nothing red anywhere.

**Rule, superseding nothing but adding a precondition to "mark every async
test":** any test file containing `@pytest.mark.asyncio` tests must use plain
pytest test classes (a bare class, or none — module-level `test_*` functions
are fine too), **never** `unittest.TestCase`. Use `setup_method`/
`teardown_method` in place of `setUp`/`tearDown`. This is a deliberate,
file-level exception to matching the existing `unittest.TestCase` style
elsewhere in the codebase (AGENTS.md's docstring/style guidance is about
*conventions*, not about silently swallowing test bodies) — call it out in a
comment at the top of any such file so a future contributor does not "fix" it
back to `unittest.TestCase` by habit.

A second, related trap: if you do use a bare class, **name it with a capital
`Test` prefix** (`TestFoo`), not this repo's usual lowercase `test_ClassName`.
`unittest.TestCase` subclasses are exempt from pytest's `python_classes`
name filter — pytest discovers them by inheritance instead — which is why the
rest of the suite gets away with lowercase names. A bare class has no such
exemption: `class test_Foo` silently collects **zero** tests, no error, no
warning, just `collected 0 items`. Prefer module-level `test_*` functions to
sidestep this entirely if a shared setup fixture is not needed.

**Added verification** — no async test is defined on a `unittest.TestCase`.

A file-level `grep` **cannot** check this and must not be used. It produces
false positives on two legitimate patterns:

1. the explanatory comment this addendum *requires* at the top of such files,
   which mentions `unittest.TestCase` by name; and
2. a file that correctly holds a sync test in a `TestCase` class **and** an
   async test in a separate bare class — which is exactly the shape a
   sync/async parity test should have (see
   `PiCN/LayerStack/test/test_stack_parity.py`).

The check needs class scope, so use the AST:

```bash
python - <<'PY'
import ast, pathlib, sys
bad = []
for p in pathlib.Path("PiCN").rglob("test_*.py"):
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        if not any("TestCase" in ast.unparse(b) for b in cls.bases):
            continue
        for fn in cls.body:
            if isinstance(fn, ast.AsyncFunctionDef) and fn.name.startswith("test"):
                bad.append(f"{p}::{cls.name}::{fn.name}")
print("\n".join(bad) if bad else "OK - no async test on a TestCase subclass")
sys.exit(1 if bad else 0)
PY
```

Expect `OK`. Any listed test is silently no-opping: `unittest` calls the
coroutine function, discards the returned coroutine, and reports **passed**
without ever running the body. (`IsolatedAsyncioTestCase` was considered as an
alternative fix — it does run async `unittest.TestCase` methods natively — but
rejected here because it would mean two different, mutually exclusive async
test mechanisms in one suite depending on base class, which is precisely the
ambiguity ADR-010 exists to avoid. Plain pytest classes keep exactly one
mechanism.)
