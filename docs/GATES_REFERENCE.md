# Lathe — Gates Reference

*The single, authoritative reference for every gate in the harness: what each one enforces, how it decides,
the exact passing condition, when it fails (and the message you'll see), how to configure it, where it's
implemented, and its known limits.*

Lathe's whole promise is that **a machine, not a person, decides what ships**. That decision is made by
*gates*. There are two families, and they run at different times:

- **Part 1 — Build-time gates** run *during* a build, mostly **per function**, and decide whether a unit of
  generated code is accepted. They are **off by default** (only the foundational acceptance gate is always
  on) and are switched on individually by env var, or all at once with `LATHE_STRICT=1`.
- **Part 2 — Standing regression gates** run *after every successful build* (via `qa/run_gates.py`) and
  keep the whole *tree* honest — no stale files, no duplicate resources, no undocumented commands. Any one
  of them going red fails the build.

A quick-reference config table is at the end ([Part 4](#part-4--configuration-quick-reference)).

> **How to read the "Implementation" lines.** Gate *logic* lives in small, harness-built, pinned pure
> functions under `projects/agentic-harness/tools/` (build-time) and `projects/agentic-harness/qa/`
> (standing). The engine (`engine_v2.py`) and CLI (`lathe.py`) call them — the citations point at both the
> decision function and its call site so you can trace any verdict end to end.

---

## Part 1 — Build-time gates (per function, composed by `LATHE_STRICT`)

`LATHE_STRICT=1` is the umbrella. `strict_mode.strict_defaults` (called at `engine_v2.py:98`) expands it into
these seven toggles **only if you haven't set them yourself** — an explicit env var always wins over STRICT:

```
LATHE_TEST_ACK=1  LATHE_REGRESSION_PROOF=1  LATHE_LINT_SPEC=block
LATHE_MUTATION_SCORE=0.5  LATHE_GATE_GLUE=1  LATHE_TEST_KIND=1  LATHE_ASSUMPTION_GATE=1
```

STRICT also requires that any FUNCTIONS plan declare `CRITERIA` (that's the traceability gate below) via
`strict_mode.strict_plan_gaps` (`engine_v2.py:102`).

### 1.0 Acceptance gate (foundational — always on)

- **What it enforces.** Generated code must make the spec's tests pass in the sandbox. This is the floor
  everything else builds on; it cannot be turned off.
- **How it decides.** The implementer's candidate code is run against the function's `tests` inside the
  isolation sandbox (`sandbox.run_unit`). The verdict is nonce-framed by the sandbox so it can't be forged by
  the code under test.
- **Passing criteria.** Every test passes (the sandbox returns `ok=True`). By convention a plan carries **≥4
  asserts** per function; `acceptance_verdict.validate_function_spec` also rejects a spec with no tests or a
  prompt under 30 chars before a build is attempted.
- **When it fails.** Any test fails, errors, or times out → the candidate is rejected, the failing candidate
  + test are **banked** in `tools/_fn_fails/`, and the analyst sharpens the spec and retries (up to
  `LATHE_TRIES`, default 3 — the Rule of Three). After the budget is spent it escalates to you, it does not
  brute-force with a bigger model.
- **Configuration.** `LATHE_TRIES` (retry budget); `LATHE_SANDBOX` (`inproc` / `docker` / `docker-ssh`)
  chooses isolation strength. No on/off — it's the floor.
- **Implementation.** `sandbox.py` (`run_unit`), `acceptance_verdict.py`
  (`compute_acceptance_verdict`, `validate_function_spec`); driven from the per-function loop in
  `engine_v2.py`.
- **Known limits.** The tests themselves are the oracle — a weak test suite accepts weak code. That gap is
  exactly what the *spec-lint*, *mutation-score*, and *test-kind* gates below exist to close.

### 1.1 Traceability gate (requirement → test)

- **What it enforces.** Under STRICT, every FUNCTIONS plan must declare `CRITERIA` — the acceptance
  requirements the tests trace back to. No requirements, no build.
- **How it decides.** `strict_plan_gaps(env, has_functions, criteria, has_artifacts)` returns a blocking
  problem when `has_functions` is true but `criteria` is `None`/empty. (It also refuses an ARTIFACTS-only
  plan under STRICT, since artifact/glue coverage isn't yet gate-enforceable.) The deeper 4-layer
  requirements matrix (Use-case → Business → Functional → Test, each tracing to its parent with no orphans)
  is checked by `sdlc_rtm.rtm_gaps`.
- **Passing criteria.** `CRITERIA` is present and non-empty; in the full RTM, every layer item has an `id` +
  `text`, no duplicate ids, and every parent is covered by a child (each UC has a BR, each BR an FR, each FR
  a TS).
- **When it fails.** `strict mode requires declared CRITERIA (requirement->test traceability) for every
  FUNCTIONS plan` — or, from the RTM, messages like `FR-3: no TS implements this requirement` /
  `BR-2: traces to nothing`.
- **Configuration.** Enabled by `LATHE_STRICT=1`. It is not separately toggleable — it's a property of
  building *under* STRICT.
- **Implementation.** `strict_mode.py` (`strict_plan_gaps`), `sdlc_rtm.py` (`rtm_gaps`); wired at
  `engine_v2.py:102`.
- **Known limits.** Guarantees the *links* exist and are well-formed; it does not judge whether a criterion
  is the *right* criterion — that's the analyst's job, sharpened by `clarify`.

### 1.2 Regression-proof gate

- **What it enforces.** A bug fix must ship a test that actually reproduces the bug — i.e. a test that
  **fails on the old code**. Prevents "fixes" that change nothing verifiable.
- **How it decides.** `proof_gate(env, old_code, old_passes_all)`. When enhancing an existing function, the
  engine runs the *new* tests against the *old* implementation. If the old code passes all of them, the new
  tests prove nothing.
- **Passing criteria.** At least one new test **fails** on the old implementation (`old_passes_all` is not
  `True`). Brand-new functions (no prior code) are exempt.
- **When it fails.** `REFUSED: every new test PASSES on the old implementation — this change ships no test
  that reproduces the bug; add a failing-on-old-code test`.
- **Configuration.** `LATHE_REGRESSION_PROOF=1|true|yes|on` (forced by STRICT). Unset → skipped.
- **Implementation.** `regression_proof.py` (`proof_gate`, `extract_def`); wired near `engine_v2.py:542`.
- **Known limits.** Only meaningful on *enhancement* builds (there must be an "old code"); a first build has
  nothing to regress against.

### 1.3 Spec-lint gate (test-quality, pre-implementer)

- **What it enforces.** The tests must actually *pin behavior* — before a single implementer token is spent.
  A shallow suite (e.g. only `assert f(1)==1`) lets the model ship confidently-wrong code that still goes
  green.
- **How it decides.** Two signals. **(a) Static gaps** (`spec_static_gaps`): missing None/empty/zero cases,
  too few assertions — *advisory*. **(b) Stub-survival probe** (the strong, blocking signal): it runs a set
  of trivial stub implementations — `return None`, `return 0`, `return ''`, `return []`, `return {}`,
  `return True/False`, `return a[0]` — against the spec's own tests, inside the sandbox. If **any** trivial
  stub passes **all** the tests, the tests don't constrain behavior.
- **Passing criteria.** No trivial stub survives (`mutation_survivors` is empty). With `warn`, static gaps
  are reported but don't block; with `block`, a surviving stub refuses the build.
- **When it fails.** Reports each surviving stub, e.g. *"returns None" survived all tests* → under `block`
  the function is refused with guidance to strengthen the tests.
- **Configuration.** `LATHE_LINT_SPEC=warn` (report only) or `block` (refuse). STRICT sets `block`. Also
  runnable standalone: `lathe lint-spec <plan.py>`.
- **Implementation.** `spec_lint.py` (`lint_function`, `_stub_survives` via `sandbox.run_unit`),
  `spec_static_gaps.py`.
- **Known limits.** The stub set is fixed and small — a suite that kills all eight stubs can still be weak in
  ways no trivial constant would expose. It's a floor on test quality, not a proof of adequacy.

### 1.4 Mutation-score gate

- **What it enforces.** The tests must be able to tell the accepted code from a subtly **broken copy** of
  it. A suite that passes even when the code is mutated is vacuous.
- **How it decides.** `mutate_code` makes small AST edits to the accepted code (flip `+`↔`-`, `<`↔`<=`,
  `and`↔`or`, `not` removal, `int`+1, string tweak), producing "mutants". Each mutant is run against the
  suite; a mutant that makes a test fail is **killed**. `mutation_gate(env, killed, total)` compares
  `killed/total` to your threshold. Equivalent mutants (behaviourally identical to the original) are meant to
  be excluded from `total` by `mutation_equiv.equivalent_over_samples`.
- **Passing criteria.** `killed / total ≥ threshold` (default **0.5** under STRICT). No mutants generated →
  gate is a no-op (nothing to judge).
- **When it fails.** `REFUSED: tests kill only K/N mutants (score S < threshold T) — the suite cannot
  distinguish the accepted code from its mutants; strengthen the tests`. Malformed inputs **fail closed**
  (`REFUSED: malformed mutation-gate inputs …`).
- **Configuration.** `LATHE_MUTATION_SCORE=<float 0.0–1.0>` (STRICT sets `0.5`). Out-of-range or unparseable
  → gate skipped with a note.
- **Implementation.** `mutation_score.py` (`mutate_code`, `mutation_gate`),
  `mutation_equiv.py` (`equivalent_over_samples`); wired near `engine_v2.py:563`, denominator at
  `engine_v2.py:708`.
- **Known limits.** **This is a bounded tripwire, not exhaustive coverage** — small operator set, capped per
  function. The equivalent-mutant exclusion was hardened in **v2.9.0** (issue #2, verified): raise-vs-return
  now counts as non-equivalent, and structural `==` is the primary oracle with `repr()` only as a fallback,
  so it fails *toward* "not equivalent" (the safe direction). It is still a fixed ~34-probe check, not
  property-based sampling — so keep stating it as "kills trivially-broken copies," never "the code is
  comprehensively tested."

### 1.5 Test-ack gate

- **What it enforces.** A human has actually **read** the AI-written tests before they become the acceptance
  oracle. The tests are the contract; someone signs it.
- **How it decides.** `tests_digest(functions)` hashes every function's name + tests into a SHA-256 digest.
  `ack_ok(env, acks, plan_name, digest)` passes only if the stored acknowledgement for this plan equals the
  *current* digest — so editing a test after acking re-arms the gate.
- **Passing criteria.** `acks[plan_name] == digest`. Run `lathe ack <plan>` to record it.
- **When it fails.** `tests NOT acknowledged — run: lathe ack <plan>`.
- **Configuration.** `LATHE_TEST_ACK=1|true|yes|on` (forced by STRICT). Unset → passes automatically.
- **Implementation.** `test_ack.py` (`tests_digest`, `ack_ok`).
- **Known limits.** It enforces that an ack *happened*, not that the reading was careful. It's an
  accountability checkpoint, not a comprehension check.

### 1.6 Test-kind gate

- **What it enforces.** The suite must contain the *kinds* of tests a contract needs — e.g. a
  property/round-trip test, an edge-case test, an error test — not just happy-path examples.
- **How it decides.** `detect_kinds(tests)` classifies each test string by heuristic into
  `{example, property, roundtrip, edge, error}` (loops + `in range`/`assert all`/`hypothesis` → property;
  encode/decode-style pairs → roundtrip; `== 0`/`[]`/`{}`/`none`/`empty` → edge; `raises`/`except`/`error`
  → error). `kind_gaps(env, required, present)` reports any required kind missing.
- **Passing criteria.** Every kind in the function's `kinds` list (or the plan's `TEST_KINDS`) is present.
  No required kinds declared → nothing to enforce.
- **When it fails.** `missing required test kind: 'property'` (etc.) — refused **before** a model call, since
  it's purely structural.
- **Configuration.** `LATHE_TEST_KIND=1` (forced by STRICT). Requirements come from per-function
  `"kinds": [...]` or a plan-level `TEST_KINDS`.
- **Implementation.** `test_kind.py` (`detect_kinds`, `kind_gaps`); wired at `engine_v2.py:637`.
- **Known limits.** As of **v2.9.0** (issue #5 fixed, verified) detection strips comments before matching (a
  `# never raises` comment no longer counts as an error test) and recognizes `sorted`/`reversed` as
  property/round-trip signals. It's still a heuristic over test *shape*, not a proof the test is good — it
  enforces *presence of a kind-shaped test*, not its quality.

### 1.7 Gate-the-glue gate

- **What it enforces.** Substantial hand-written **glue** (the wiring the model didn't generate) can't ship
  ungated — it must be exercised by an INTEGRATION test.
- **How it decides.** `count_glue_lines(glue)` counts non-blank, non-comment lines in the plan's `GLUE`.
  `glue_gap(env, glue_lines, has_integration, threshold)` refuses when glue exceeds the threshold and the
  plan has no INTEGRATION block.
- **Passing criteria.** Glue is trivial (`glue_lines ≤ threshold`, default **2** via `LATHE_GLUE_MAX`) **or**
  the plan has a non-empty `INTEGRATION` block.
- **When it fails.** `REFUSED: N lines of hand-written GLUE with no INTEGRATION test — the wiring is ungated;
  add an INTEGRATION block that imports the module and asserts its behavior`.
- **Configuration.** `LATHE_GATE_GLUE=1` (forced by STRICT); `LATHE_GLUE_MAX=<int>` sets the trivial-glue
  threshold (default 2).
- **Implementation.** `glue_gate.py` (`count_glue_lines`, `glue_gap`); wired near `engine_v2.py:959`.
- **Known limits.** As of **v2.9.0** (issues #4 fixed, verified) it counts *AST statements* (so `;`-packed
  one-liners no longer evade the threshold) and requires the INTEGRATION block to contain an `assert` (a
  `pass` placeholder no longer counts as "exercised"). It still checks that an INTEGRATION test *exists*, not
  that it's thorough. Glue remains hand-written and is marked as such in the provenance count.

### 1.8 Assumption gate

- **What it enforces.** The build won't proceed while a **material, unconfirmed assumption** about the goal
  is outstanding — encoding, rounding, ordering, empty-input behavior, etc. No silent guessing.
- **How it decides.** An adversarial `assumption-auditor` writes a ledger of assumptions, each with a
  `materiality` of `high`/`med`/`low`. `unconfirmed_blockers(assumptions, confirmed, policy)` returns every
  assumption at or above the policy's level that isn't in the committed `confirmed` set. You resolve each
  (`lathe assume --resolve`) — accept, pick an offered option, or state intent — recorded in
  `<plan>.decisions.md`.
- **Passing criteria.** No unconfirmed assumption at or above the scrutiny level remains.
- **When it fails.** The build refuses and prints the outstanding blockers, pointing you to resolve them (or
  lower scrutiny). Skipping stays blocking; bulk `--accept-all` is a separate, logged opt-in.
- **Configuration.** `LATHE_ASSUMPTION_GATE=1` turns it on (forced by STRICT). `LATHE_ASSUMPTION_POLICY`
  sets scrutiny: `off`/`none`/`advisory` (never blocks) · **`high`** (default — only high-materiality
  blocks) · `med` (high+med) · `all`/`low` (everything). Also settable via config `assumptions.scrutiny`.
- **Implementation.** `assumption_logic.py` (`blocking_assumptions`, `unconfirmed_blockers`,
  `parse_assumptions`, `spec_digest`); wired at `engine_v2.py:141`.
- **Known limits.** As of **v2.9.0** (issue #6 fixed, verified) materiality is handled fail-closed: an
  unranked/garbled/non-canonical label (empty, `medium`, `critical`, …) is treated as `high` rather than
  silently defaulting to `med`, so a mislabeled material assumption can't slip under the default `high`
  scrutiny. It still surfaces only assumptions the auditor *finds*, and can't guarantee your resolution is
  correct — a hardening of the front end, not a proof of intent.

---

## Part 2 — Standing regression gates (`qa/run_gates.py`)

These run automatically after every successful build (the engine resolves `projects/<proj>/qa/run_gates.py`
from the plan path). A non-zero exit from any check makes the whole build **RED** — so a build that leaves
the tree dirty cannot ship. Each is also runnable by hand (`python qa/<gate>.py`, most take `--list`).

| # | Check name | Gate file |
|---|---|---|
| 1 | `tree_no_stale_dups` | `stale_gate.py` |
| 2 | `no_duplicate_resources` | `resource_dups_gate.py` |
| 3 | `capability_registry` | `registry_gate.py` |
| 4 | `pristine_tree` | `pristine_gate.py` |
| 5 | `lint_no_real_bugs` | `lint_gate.py` |
| 6 | `docs_not_drifted` | `docs_drift_gate.py` |
| 7 | `env_not_drifted` | `env_drift_gate.py` |

### 2.1 Stale / retirement gate (`tree_no_stale_dups`)

- **What it enforces.** No backup/duplicate/superseded files linger in `tools/` or `plans/`.
- **How it decides.** Walks the source dirs and matches filenames against a retire pattern
  (`_backup`, `.bak`, `_bak`, `_old`, `_v1`, `_v2_old`, `_copy`, `copyN`, `.orig`, `~`, `.tmp`), skipping
  `_archive`/`_legacy`/`_retired`/`_fn_fails`/`__pycache__`.
- **Passing criteria.** No matching files in the main tree. **Fails** (exit 1) if any exist — the fix is
  *decide-then-archive*: move it to `_archive/<date>-<reason>/` (kept, not deleted).
- **When it fails.** `STALE FILES in the agentic-harness tree (retire to _archive/…)`.
- **Configuration.** `--list` to preview candidates. Pattern is in `RETIRE_PAT`.
- **Implementation.** `qa/stale_gate.py`. **Known limits.** Name-based — a duplicate with a *legitimate*
  name (two real `harness.db`) is invisible to it; that's what the resource-dups gate is for.

### 2.2 Resource-dups gate (`no_duplicate_resources`)

- **What it enforces.** Exactly one canonical data resource per basename — no two `*.db`/`*.sqlite` files
  with the same name in different folders (the "multi-DB mess").
- **How it decides.** Collects every `.db`/`.sqlite`/`.sqlite3` under the project (skipping vcs/vendor/cache
  dirs — deliberately **not** skipping `qa/`) and calls `duplicate_basenames`.
- **Passing criteria.** No basename appears twice. **Fails** if any duplicate group exists.
- **Configuration.** `--list` prints the duplicate groups. Scope is resources-only (kept tight so it never
  false-fails on `.py`).
- **Implementation.** `qa/resource_dups_gate.py`, `tools/duplicate_basenames.py`.
- **Known limits.** Resource files only, by design.

### 2.3 Registry gate (`capability_registry`)

- **What it enforces.** The capability registry (`capabilities.json`) stays consistent — one canonical
  `live` implementation per capability.
- **How it decides.** `registry.audit()` flags an invalid status, a superseded-yet-`live` entry, two `live`
  entries sharing one canonical artifact, or a `live`/`designed` capability whose file is missing on disk.
- **Passing criteria.** No audit problems. Empty/absent registry → passes (opt-in — a project that hasn't
  declared capabilities isn't penalised).
- **When it fails.** `registry_gate: capability registry DIVERGENCE (fix capabilities.json)` + specifics.
- **Configuration.** `--list` prints the live capability map.
- **Implementation.** `qa/registry_gate.py`, `tools/registry.py`.

### 2.4 Pristine gate (`pristine_tree`)

- **What it enforces.** No corrupt/half-written code in the tree — every plan and generated module must
  parse as Python. Git-independent (cleanliness is a property of the tree, not of git).
- **How it decides.** Recursively `ast.parse`s every non-test `.py` under the source dirs (skipping
  quarantine/cache dirs); any file that fails to parse is an offender.
- **Passing criteria.** Everything parses. **Fails** if any file is unparseable. `lathe clean` quarantines
  offenders to `_archive/`.
- **When it fails.** Lists each offender with the parse error.
- **Configuration.** `--list` to see offenders.
- **Implementation.** `qa/pristine_gate.py`.

### 2.5 Real-bug lint gate (`lint_no_real_bugs`)

- **What it enforces.** Generated modules contain no *actual defects* — undefined name, redefinition, broken
  `%`-format, syntax slip — as opposed to style nits.
- **How it decides.** Runs `ruff check --select F,E9 --ignore F401,F841` over `tools/`. `F`/`E9` are the
  pyflakes/error rules that mean a real bug; unused imports/vars (`F401`/`F841`) are reported **advisory**
  only (generated code needn't be PEP8-pretty and is never hand-edited to satisfy style).
- **Passing criteria.** Zero hard findings. **Skips cleanly** (exit 0) if `ruff` isn't installed —
  never fails a build for a missing optional linter.
- **When it fails.** Prints the ruff findings; exit 1.
- **Configuration.** Rule sets are `_HARD` in the file. Install `ruff` to activate.
- **Implementation.** `qa/lint_gate.py`.

### 2.6 Docs-drift gate (`docs_not_drifted`)

- **What it enforces.** Every CLI command is documented (with an example) — you can't add a command and
  forget to write it up.
- **How it decides.** Extracts the command names from `lathe.py`'s dispatch `table` (by AST) and checks each
  appears in `LATHE_COMMANDS.md` via `undocumented_commands`.
- **Passing criteria.** No command missing. **Skips** if `lathe.py`/`LATHE_COMMANDS.md` aren't at the
  expected root.
- **When it fails.** `docs_drift_gate: N command(s) undocumented (add an example to LATHE_COMMANDS.md): …`.
- **Implementation.** `qa/docs_drift_gate.py`, `tools/undocumented_commands.py`.

### 2.7 Env-drift gate (`env_not_drifted`)

- **What it enforces.** Every env var the code actually reads is documented in `env_catalog.py` (what
  `lathe env` prints) — a new env var can't drift in undocumented. (Added from PR#1's CLI review.)
- **How it decides.** `env_logic.extract_env_vars` scans `lathe.py`, `engine_v2.py`, `lathe_api.py`,
  `lathe_mcp.py`, and `tools/*.py` for every var read, subtracts an OS/interpreter ignore set (`PATH`,
  `HOME`, `OPENAI_API_KEY`, …), and fails if any user-facing var is absent from `env_catalog.REGISTRY`.
  "Documented but unused" is advisory only.
- **Passing criteria.** Every code-read var is cataloged. **Skips** if the core files aren't at root.
- **When it fails.** Lists the undocumented vars.
- **Implementation.** `qa/env_drift_gate.py`, `tools/env_logic.py`, `env_catalog.py`.

---

## Part 3 — Composition, precedence, and how to drive them

- **Off by default.** Only the acceptance gate (1.0) and the standing gates (Part 2) are always active. The
  seven build-time rigor gates are opt-in.
- **STRICT is the switch.** `LATHE_STRICT=1` composes all seven (§1.1–1.8) with sane defaults and requires
  `CRITERIA`. This is the intended production posture.
- **Explicit vars win.** If you set, say, `LATHE_MUTATION_SCORE=0.8` yourself, STRICT will *not* override it
  down to 0.5 — `strict_defaults` only fills toggles you left unset (`strict_mode.py:24`). Use this to run
  STRICT-but-stricter, or STRICT-minus-one. **Opt a gate out with a non-empty disabling value**, e.g.
  `LATHE_STRICT=1 LATHE_TEST_ACK=0` — note that an **empty string is treated as *unset*** (`current != ''`),
  so STRICT will fill it; only a non-empty value (`0`, a lower threshold, `off`, …) survives as an override.
  (Verified by executed probe — see `GATES_STRESS_TEST.md`.)
- **Config file mirror.** Several gates also read from `lathe.config.json` (e.g. `assumptions.scrutiny` →
  `LATHE_ASSUMPTION_POLICY`). Env always overrides config.
- **Run a gate standalone.** `lathe lint-spec <plan>`, `lathe gate`, and each `python qa/<gate>.py [--list]`
  let you check a gate without a full build.

---

## Part 4 — Configuration quick reference

**Build-time gates** (per function; `LATHE_STRICT=1` sets the "STRICT default" column):

| Gate | Env var | Values | STRICT default | Refuses when |
|---|---|---|---|---|
| Acceptance (floor) | `LATHE_SANDBOX`, `LATHE_TRIES` | `inproc`/`docker`/`docker-ssh`; int | — (always on) | a spec test fails |
| Traceability | `LATHE_STRICT` (+ plan `CRITERIA`) | `1` | on | FUNCTIONS plan has no `CRITERIA` |
| Regression-proof | `LATHE_REGRESSION_PROOF` | `1`/`true`/… | `1` | new tests all pass on old code |
| Spec-lint | `LATHE_LINT_SPEC` | `warn` / `block` | `block` | a trivial stub passes all tests |
| Mutation-score | `LATHE_MUTATION_SCORE` | float `0.0`–`1.0` | `0.5` | `killed/total` below threshold |
| Test-ack | `LATHE_TEST_ACK` | `1`/`true`/… | `1` | tests not acked (or edited since) |
| Test-kind | `LATHE_TEST_KIND` (+ `kinds`/`TEST_KINDS`) | `1`/`true`/… | `1` | a required test kind is absent |
| Gate-the-glue | `LATHE_GATE_GLUE`, `LATHE_GLUE_MAX` | `1`/`true`/…; int (dflt 2) | `1` | glue > max lines, no INTEGRATION |
| Assumption | `LATHE_ASSUMPTION_GATE`, `LATHE_ASSUMPTION_POLICY` | `1`; `off`/`high`/`med`/`all` | `1`, `high` | a material assumption is unconfirmed |

**Standing gates** (whole-tree, post-build; no per-gate off switch — they're the cleanliness floor):

| Check | Gate file | Fails when | Manual run |
|---|---|---|---|
| `tree_no_stale_dups` | `stale_gate.py` | backup/dup/old file in `tools`/`plans` | `python qa/stale_gate.py --list` |
| `no_duplicate_resources` | `resource_dups_gate.py` | two DBs share a basename | `… --list` |
| `capability_registry` | `registry_gate.py` | `capabilities.json` divergence | `… --list` |
| `pristine_tree` | `pristine_gate.py` | a `.py` won't parse | `… --list` |
| `lint_no_real_bugs` | `lint_gate.py` | ruff `F`/`E9` finding (skips w/o ruff) | `python qa/lint_gate.py` |
| `docs_not_drifted` | `docs_drift_gate.py` | a command missing from `LATHE_COMMANDS.md` | `python qa/docs_drift_gate.py` |
| `env_not_drifted` | `env_drift_gate.py` | a code-read env var not in `env_catalog.py` | `python qa/env_drift_gate.py` |

---

*The fail-open findings from the gate stress-test (`GATES_STRESS_TEST.md`) were **fixed in v2.9.0** —
mutation-equivalence hardening (#2), glue line-packing + placeholder-INTEGRATION (#4), test-kind comment
stripping (#5), assumption fail-closed materiality (#6), docs-drift whole-word + broadened stale pattern
(#8), and the REST API token scrub + status semantics (#3) — all independently re-verified. The known-limit
notes above reflect the post-v2.9.0 behavior. Verify any gate on your own machine — every claim here is
traceable to the cited source.*
