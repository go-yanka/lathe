# What's Available to You — a practical guide for projects using Lathe

You vendor Lathe (see `VENDORING.md`). This page is the plain-English list of **everything you can use right
now** (canonical `2026-07-01q`), what each thing is for, the command, and a real example. Re-vendor the latest
canonical to get all of it.

> How to read this: each capability says **what it does**, **when to use it**, the **command**, and a
> one-line **example**. Nothing here is theoretical — it all ships and is gate-verified.

---

## 1. Build tested code from a spec (the core)
**What:** you write a spec (a *plan*: functions + tests); a local model implements it under those tests;
passing code is content-hash **pinned** so rebuilds are free and deterministic. You never hand-edit generated
code — fix the spec and rebuild.
**Use it when:** you need a new pure helper/function and want it *tested and reproducible*.
```
python lathe.py do "parse a duration like '2h30m' into seconds"
python lathe.py build projects/<you>/plans/my_plan.py
```

## 2. Check your TESTS are actually good  ⭐ (new)
**What:** `lint-spec` scores a plan's tests *before* building. A **mutation probe** runs trivial stub impls
(`return None`/`0`/identity) against your tests — if a stub passes them all, your tests don't pin behavior.
**Use it when:** always, before trusting a green build. Set `LATHE_LINT_SPEC=block` to fail a build on weak tests.
```
python lathe.py lint-spec projects/<you>/plans/my_plan.py
```

## 3. Run untrusted code safely — real isolation  ⭐ (new)
**What:** tests run in an isolated sandbox with an unforgeable verdict. For fully-untrusted plans, run them in a
**network-less, read-only container** — locally (`docker`) or on a remote host over SSH (`docker-ssh`, when the
box has no local docker). Verified: no network, read-only FS, no host files.
**Use it when:** building/running plans you didn't author.
```
LATHE_SANDBOX=docker-ssh LATHE_DOCKER_SSH=rig python lathe.py build <plan>
```

## 4. See exactly what happened — structured logs  ⭐ (new)
**What:** every run writes `runs/<id>.jsonl` (start → every model call with latency+tokens → result), **secrets
redacted**. A bug report becomes self-diagnosing.
**Use it when:** anything fails, or you file an issue — attach the run log.
```
python lathe.py logs --tail          # the last run's full trace
python lathe.py logs <run_id>        # a specific run
```

## 5. Honest metrics — build success, cost, churn  ⭐ (new)
**What:** aggregates your run ledger into evidence: build-success rate, local-vs-frontier split, tokens,
first-pass rate, escalations.
**Use it when:** you want real numbers, not vibes.
```
python lathe.py metrics summary
```

## 6. Gate "unit-green but wrong on real data"  ⭐ (new — your-product)
**What:** reusable data-quality primitives — `distribution_anomalies` (all-same/collapsed output),
`dangling_references` (orphan FKs), `incomplete_records` (never-populated fields). Wire them into your own
`qa/data_gates.py` that runs on your REAL output. Framework is the harness's; the specific checks are yours
(vendoring boundary). Full guide: **`DATA_QUALITY.md`**.
**Use it when:** your code is unit-correct but you need to catch garbage on the actual corpus.
```python
from distribution_anomalies import distribution_anomalies
problems = distribution_anomalies(my_scores)   # e.g. flags a scorer returning the same value for everything
```

## 7. Deterministic e2e tests for LLM pipelines  ⭐ (new — a downstream project)
**What:** a record/replay **cassette** proxy. Record your model calls once; replay them offline by request-hash
so a slow, nondeterministic LLM-pipeline test runs in **milliseconds, deterministically, every build**.
**Use it when:** your correctness invariant only breaks at scale through the real model pipeline.
```
# record once (forwards to the real endpoint + saves), then replay offline forever
LATHE_GATE_RECORD=1 LATHE_CASSETTE=plans/pipe.cassette.json \
  LATHE_CASSETTE_UPSTREAM=http://127.0.0.1:8090 python tools/cassette_proxy.py
# then point your pipeline's model base URL at the proxy (:8791)
```

## 8. Multi-lens code review — real Compound-Engineering  ⭐ (upgraded)
**What:** `lathe review` runs the **actual CE reviewer personas** (security, correctness, adversarial, data,
perf, reliability, api, maintainability, testing, ui) — vendored from upstream, not reimplemented — plus
Lathe's field doctrine. Catches design/security bugs tests can't.
**Use it when:** before shipping a change.
```
python lathe.py review all projects/<you>/runtime/*.py
python lathe.py review correctness adversarial <file>
```

## 9. Read a codebase by its STRUCTURE — repo-map  ⭐ (new)
**What:** `lathe map` emits a multi-language code-structure map (names, kinds, **signatures**, scopes) via
universal-ctags — Python, **JS**, ~150 languages — so a large model reads the structure instead of every file.
**Use it when:** giving an LLM context about a codebase without dumping full files. (Needs `ctags` on PATH:
`winget install UniversalCtags.Ctags`.)
```
python lathe.py map projects/<you>/runtime/
```

## 10. Named, transparent WORKFLOWS  ⭐ (new)
**What:** end-to-end processes — `code-review`, `bug-fix`, `enhancement`, `doc-review`, `sdlc`, `new-project` —
as ordered steps (`[AUTO]` runs, `[GATE]` checks, `[YOU]` judgment). See exactly how the harness handles a job
before running it.
**Use it when:** you want a predictable, repeatable process.
```
python lathe.py flow bug-fix                 # show the steps
python lathe.py flow bug-fix --run <plan>    # execute the automatable steps
```

## 11. Force the METHODOLOGY, not just green tests  ⭐ (new)
**What:** one switch, `LATHE_STRICT=1`, makes the *kind and rigor* of testing non-optional on a build:
a change must ship a test that fails on the old code (regression-proof); trivial AST mutants must be killed
(mutation-score, a bounded tripwire — not exhaustive); a human acks the test set (`lathe ack`); declared
test kinds (`property`/`edge`) are required; hand-written glue must have an integration test; every
acceptance criterion must map to a named test (`lathe trace`); and an adversarial auditor's unstated
HIGH-materiality assumptions must be confirmed (`lathe assume`). Each is also switchable on its own.
**Use it when:** the code matters and "unit-green but under-tested" is unacceptable. The `bug-fix`,
`enhancement`, and `sdlc` workflows already build under STRICT.
```
LATHE_STRICT=1 python lathe.py build <plan>     # all seven gates on
python lathe.py trace <plan>                      # criterion → test → pin → model matrix
python lathe.py assume <plan> --resolve            # decide each of the goal's silent assumptions (per-item)
```

## 12. Sharpen the requirement before any code  ⭐ (new)
**What:** `lathe clarify "<goal>"` runs a **requirements liaison** that interrogates you (inputs, outputs,
success criteria, constraints, edge cases, non-goals) and writes a `CLARIFIED_GOAL.md` brief with testable
acceptance criteria — *before* the harness starts designing. It's step 0 of the `sdlc` workflow.
**Use it when:** the goal is fuzzy and you'd rather resolve ambiguity up front than debug a confidently-wrong build.

## 13. Keep your tree clean + know what's live
- `python lathe.py gate` — the standing gates (no stale/dup files, one canonical DB, no corrupt files, real-bug
  lint, docs-not-drifted). Run every build.
- `python lathe.py whatis <capability>` — the source of truth for "which artifact is LIVE" (kills the
  duplication trap).
- `python lathe.py dups` — advisory: same logic in two places.
- `python lathe.py clean` — quarantine corrupt/backup files (git-independent).

---

## How to get all of this
1. **Re-vendor** the latest canonical (`2026-07-01q`) into your project — copy `engine_v2.py`, `lathe.py`,
   `projects/agentic-harness/` (tools, plans, qa, `ce_personas/`), and the docs. Keep YOUR product layer
   untouched. Verify: `python lathe.py selftest` + `python lathe.py gate`.
2. **Optional setup** (each degrades gracefully if absent):
   - `ctags` → enables `lathe map` (`winget install UniversalCtags.Ctags`)
   - docker on a rig + SSH → enables the `docker-ssh` untrusted-plan sandbox
   - `ruff` → the lint gate (else it skips)
3. **Full command reference with examples:** `LATHE_COMMANDS.md`. **How it works + why:** `ARCHITECTURE.md`.
   **Threat model:** `SECURITY.md`. **Data gates:** `DATA_QUALITY.md`.

## Found a problem? File it — the loop is real
`python lathe.py report "<title>"` files into the shared issue queue; include the run log
(`lathe logs <id>`). Fixes land in canonical and you re-vendor. That feedback loop is part of the design.
