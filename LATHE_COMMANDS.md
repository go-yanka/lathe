# Lathe — Command Reference (every command, with a runnable example)

Lathe treats AI code generation like a **build system, not a conversation**: you write a *spec* (a plan), a
local model implements it under *test gates*, passing code is *pinned* (content-hashed, so rebuilds are free
and deterministic), and you never hand-edit generated code — you fix the spec and rebuild.

Run `python lathe.py <command>`. Below, each command shows **what it does**, a **runnable example**, and the
**expected output** (trimmed). See `ARCHITECTURE.md` for *how* it all fits together and *why*.

---

## Build — turn a spec into gated, pinned code

### `lathe "<goal>"` / `lathe do "<goal>"`
Draft a spec for a goal, build it on the local model under gates, pin it — one shot. The analyst (a frontier
model) writes the functions + tests; the local model implements; tests gate; green code is pinned.
```
$ python lathe.py do "a function that parses a duration like '2h30m' into seconds"
  parse_duration   PASS (qwen)   1 tries  (5 tests)
  -> built 1 function, pinned. module: projects/agentic-harness/tools/parse_duration.py
```

### `lathe build <plan.py>`
Build an explicit plan file (you wrote the spec). Reproducible: an unchanged plan reuses its pins instantly.
```
$ python lathe.py build projects/agentic-harness/plans/auto_070.py
  registry_violations PASS (qwen)   1 tries  (11 tests)
  build_ok: true   run report: .../RUN_REPORT.md   metrics -> runs.jsonl
```

**Change-proof (`LATHE_REGRESSION_PROOF=1`):** ANY changed function — bug fix or enhancement — is refused
unless ≥1 of its new tests FAILS on the old accepted implementation (a change must ship a test that proves
the new behavior; refused before any generation; new functions and unchanged pins unaffected; default off).

**Mutation-score gate (`LATHE_MUTATION_SCORE=<0..1>`):** after a function passes its tests, the engine
seeds deterministic single-fault mutants of the accepted code (arithmetic/comparison/boolean/membership/
identity operators + int and string constants) and requires the suite to kill ≥ that fraction before pinning.
**Equivalent mutants** (no input can distinguish them — e.g. slack in a guard constant) are detected by a
deterministic differential probe and **excluded** from the score, so a complete suite is never falsely
blocked. A function with **no mutable nodes** is reported `unmeasurable` (a ledger flag), never silently
passed. Scope, stated honestly: this is a bounded tripwire for vacuous tests (a small operator set, capped
per function via `LATHE_MUTATION_LIMIT`), **not** exhaustive mutation coverage.

**Required test-KIND per contract (`LATHE_TEST_KIND=1`, forced by STRICT):** comprehensiveness isn't only
"how many mutants die" — it's whether the *right shape* of test exists. A function may declare
`'kinds': ['property', 'edge']` (or the plan a default `TEST_KINDS`); when armed, a unit whose tests don't
contain its declared kinds is **refused** (kinds are detected structurally — property/roundtrip/edge/error/
example — no model call). The `enhancement` workflow asks you to declare a **property** test per invariant.

**Gate the glue (`LATHE_GATE_GLUE=1`, forced by STRICT):** `GLUE` is the architect's hand-written wiring
appended after the gated functions — the most bug-prone part, otherwise shipped unverified. When armed, a
plan whose substantive GLUE (more than `LATHE_GLUE_MAX`, default 2 lines) has no `INTEGRATION` block is
**refused** — the wiring must be exercised by an integration test. This is what lets the harness claim *no
code* ships untested, not just *no function*.

**STRICT / SDLC mode (`LATHE_STRICT=1`):** the enforcement umbrella — forces **all** proof mechanisms for
**all** development, no picking and choosing: declared `CRITERIA` (requirement→test traceability) required
on every plan, tests must be acknowledged (`lathe ack`), new code's tests must survive the stub probe
(`LATHE_LINT_SPEC=block`), and changed code must carry a failing-on-old-code test. An explicitly-set env
var still wins over the umbrella — and the accepted code must beat a **mutation-score threshold**
(`LATHE_MUTATION_SCORE=0.5` under strict): deterministic AST mutants of the accepted implementation must be
killed by the suite or the code will not pin. The `bug-fix`/`enhancement` workflows build under this mode —
following the SDLC process is enforced, not advisory.

### `lathe chat`
Interactive REPL — each line is a goal or a command (`build ...`, `status`, `quit`). Survives transient
failures (a proxy/rig blip prints an error and keeps the session alive).
```
$ python lathe.py chat
lathe> slugify a title string
  -> green (1 built)
lathe> quit
```

### `lathe lint-spec <plan.py>`  *(test-quality)*
Score a plan's **tests** *before* building: static gaps + a **mutation probe** (does a trivial stub impl —
`return None`/`0`/identity — pass every test? then the tests don't pin behavior). Set `LATHE_LINT_SPEC=warn`
or `=block` to run it as a pre-implementer gate during a build.
```
$ python lathe.py lint-spec projects/agentic-harness/plans/auto_070.py
  [warn ] registry_violations
          advisory: no zero case
  0/1 function(s) have BLOCKING weak tests
```

### `lathe flow [<name>] [--run <targets>]`  *(workflows)*
Named, transparent end-to-end **workflows** — `code-review`, `bug-fix`, `enhancement`, `doc-review`,
`new-project`. `lathe flow` lists them; `lathe flow <name>` prints an up-front **contract** (when to use it,
entry criteria, the deliverable, and definition-of-done) followed by the exact ordered steps — so you know
what to expect *before* running. `--run` executes the automatable `[AUTO]`/`[GATE]` steps in order (reusing
the real `lathe` commands — no duplicated logic), flags the human-judgment `[YOU]` steps, then prints a
**transparent run report** and a **fail-loud `PASS`/`BLOCKED` verdict** (a step that can't do its job — e.g. a
missing target — is `BLOCKED` with a non-zero exit, never a false "green"). Definitions are data
(`tools/workflows.py`); the report/verdict logic is itself harness-built (`tools/flow_report.py`).
```
$ python lathe.py flow bug-fix
workflow: bug-fix — Reproduce -> diagnose -> fix the SPEC -> verify -> review -> release.
  when:        A build/behavior is wrong and you need it corrected at the source, not patched.
  entry:       You can name the failing plan and reproduce it.
  deliverable: The SPEC/tests pin the correct behavior; a green rebuild; the fix reviewed.
  done when:   Rebuild green, tree clean, review clear, issue resolved + released.

  1. [AUTO] Reproduce: rebuild the failing plan  ->  lathe build {plan}
  2. [AUTO] Diagnose: read the full run trace     ->  lathe logs --tail
  3. [AUTO] Are the tests even GOOD?              ->  lathe lint-spec {plan}
  4. [YOU]  Fix the SPEC/tests (never hand-edit generated code), then rebuild
  ...
$ python lathe.py flow doc-review --run <file>     # ... ends in: verdict: PASS
```

## Quality — gates and review

### `lathe gate`
Run the standing cleanliness + lint gates on the tree (stale/dup files, one canonical DB, capability registry,
no corrupt files, no real-bug lint). Fast, deterministic, git-independent.
```
$ python lathe.py gate
tree_no_stale_dups     PASS   no backup/dup/superseded files
capability_registry    PASS   8 capabilities, one canonical 'live' each
lint_no_real_bugs      PASS   no undefined-name/syntax/format defects
regression clean (5 checks)
```

### `lathe review [auto|lens…|all] <files...>`
Multi-file, multi-lens Compound-Engineering review (read-only). Lenses: security, correctness, adversarial,
data, perf, reliability, api, maintainability, testing, ui. Findings fold into the owning plan and regenerate.
Use **`auto`** to let the **decider** pick the appropriate persona(s) for the code's domain (correctness +
adversarial always, plus the domain specialists it matches — e.g. `security`+`reliability` for network/subprocess
code). This is what the `code-review`/`bug-fix` workflows now use, so the right minds are invoked automatically.
```
$ python lathe.py review auto lathe_mcp.py
decider selected lenses for this code: correctness, adversarial, security, reliability
========== lathe review: correctness (1 file) ==========
  ... findings by severity ...
```

### `lathe verify <plan.py>`
Rebuild a plan and confirm it still passes its gates (a targeted regression for one plan).

### `lathe selftest`
Exercise every Lathe capability and report PASS/FAIL — the confidence check before relying on it.
```
$ python lathe.py selftest
  [PASS] build + content-hash pins
  [PASS] repair feedback loop
  ...
12/12 capabilities confirmed via CLI.
```

## Autonomy — the board and the driver

### `lathe auto "<objective>"`
Decompose a big objective into small jobs and keep building them (the planner loop + repair loop).

### `lathe decompose <plans...>` / `lathe run [N]`
`decompose` seeds the board (one task per plan, wiring `DEPENDS_ON`); `run` is the dispatcher that drives the
whole board to gated-green (the overnight multi-task driver).

### `lathe board` / `lathe status`
`board` shows the kanban task list; `status` shows a one-glance summary (board counts, pins, ledger tail, and
the implementer/analyst endpoints derived from your env).
```
$ python lathe.py status
  board:   {'done': 12, 'todo': 0}
  pins:    47 approved impls
  implementer (127.0.0.1:8089): up
  analyst (127.0.0.1:8787): up
```

### `lathe wait <task>` / `lathe resume <task> [signal]` / `lathe waiting`
Park a long job **dormant** awaiting an external signal (human approval, a slow dep, a time window), resume it
from durable board state, and list what's waiting. (Event-driven pause/resume.)

### `lathe checkpoint [list|restore]`
Git snapshot / list / restore for safe rollback (`refs/harness/ckpt`, doesn't touch HEAD).

## Introspection — know what's live

### `lathe whatis <capability>`
The capability **source of truth** — answers "which artifact is LIVE for X" by lookup, not by grepping N copies
and guessing. Fixes the duplication/divergence trap.
```
$ python lathe.py whatis planner
planner -> tools/planner_prompt.py (live)  entrypoint: build_planner_prompt
```

### `lathe map <path...>`  *(repo-map)*
Multi-language **code-structure map** via universal-ctags (the real OSS C tool — we shell out to it, not
reimplement it). Emits names, kinds, **signatures**, and scopes across ~150 languages (Python, JS, …) so a large
model reads the *structure* instead of every full file — less context, fewer tool calls. Needs `ctags` on PATH.
```
$ python lathe.py map projects/agentic-harness/tools/spec_lint.py
spec_lint.py:
  function spec_static_gaps(t)
  function _stub_survives(fname, body, tests)
  function lint_function(fname, tests)
  function lint_plan(plan_path)
```

### `lathe dups [--min N]`
Advisory structural-duplication report — flags functions sharing an AST shape (rename-safe). Catches "same
feature built twice."

### `lathe plans` / `lathe metrics`
`plans` lists available plan files; `metrics` summarizes recent engine runs from the ledger (success rate,
cost/function, churn).

### `lathe logs [<run_id>] [--tail] [--grep <s>]`  *(observability)*
Read the structured per-run logs. Every build writes `runs/<run_id>.jsonl` (start → each model call with
latency+tokens → result), secrets redacted. This is what you attach to a bug report.
```
$ python lathe.py logs --tail
=== run 20260630-235607-981b (3 events) ===
  ... start / model_call {elapsed_s, tokens} / result {build_ok} ...
```

## Agents — instantiate expert personas on demand

### `lathe agent "<need>" [--spawn]`
**Load the program.** Match a capability need to the best expert persona — from the **vendored** set or **fetched
on demand** from a permissively-licensed source — then inject it into whatever endpoint is configured
(**LLM-independent**: any OpenAI-compatible agent or client / Claude subscription proxy / Claude API / local — a persona is just prompt text).
`lathe agent "<need>"` reports the best match; `--spawn` fetches it (license-gated) and caches it with attribution.
The inventory is `projects/agentic-harness/agents/catalog.json`; the decider is harness-built (`tools/agent_router.py`).
**Compliance:** auto-fetch is gated to permissive licenses (MIT/Apache/BSD/ISC/Unlicense/CC0); anything else
(GPL, unlicensed/`NOASSERTION`) is catalogued but **never** auto-fetched. Fetched files land in `agents/_fetched/`
(gitignored — a per-user cache, not redistributed) with a `SOURCE` note.
```
$ python lathe.py agent "backend api design" --spawn
best match: backend-architect  [wshobson/agents · MIT]
  SPAWNED: 18356 bytes -> agents/_fetched/backend-architect.md (+ SOURCE attribution). Ready to inject into any endpoint.
```

### `lathe ack <plan> [--yes]`
**Gate the analyst's tests** — the asserts define what "correct" means, so they deserve a human read before the
build certifies them. Shows every function's test set and records an acknowledgement keyed by a **digest of the
exact tests**; set `LATHE_TEST_ACK=1` and the engine **refuses to build** a plan whose tests are un-acked — and
because any rewrite (including by the spec-repair loop) changes the digest, silently weakened tests force a
re-read. Opt-in: without `LATHE_TEST_ACK=1` nothing changes.
```
$ python lathe.py ack examples/hello.py --yes
TESTS UNDER REVIEW — these asserts DEFINE correct behavior for this build:
  greet:
      assert greet('Ada') == 'Hello, Ada!'
acknowledged: hello.py (digest 3f2a91c04b7e...) -> examples/.test_ack.json
```

### `lathe trace <plan> [model]`
**Requirement→test→pin→model traceability** — the compliance artifact, enforced at the validator. A plan may
declare acceptance criteria; **a criterion not mapped to ≥1 named, existing test is refused** (an unmapped
requirement is a requirement nothing verifies — dangling function refs and out-of-range test indexes are
refused too). `lathe trace` then emits the matrix: which test proves which criterion, the content-hash **pin**
of the accepted implementation, and the model that wrote it.
```python
CRITERIA = [
  {"id": "AC-1", "text": "adds two to any int",  "tests": ["add2"]},      # all of add2's tests
  {"id": "AC-2", "text": "handles negatives",    "tests": ["add2:1"]},    # one named assert
]
```
```
$ python lathe.py trace plans/my_plan.py
TRACEABILITY MATRIX — my_plan.py  (model=openai:local)
CRIT     FUNCTION           PIN            MODEL          TEST
AC-1     add2               8c41d2a90b7f   openai:local   assert add2(1) == 3
AC-2     add2               8c41d2a90b7f   openai:local   assert add2(-2) == 0
2 criteria, 2 covered, 0 unresolved; 3 matrix rows.
```

### `lathe sdlc "<goal>" [--out <dir>]`
**SDLC authoring, enforced.** The analyst writes LAYERED, ID-traced requirements — UC (use case) → BR
(business requirement) → FR (functional requirement) → TS (technical spec) — and the harness-built **RTM
gate refuses** the set unless every item traces down AND is covered up (no orphans, no dangling refs; one
retry with the gaps fed back, then fail loud). Output: `REQUIREMENTS.md` + `rtm.json` + a suggested plan
`CRITERIA` block (each TS becomes an acceptance criterion) — feed it to a **STRICT-mode** build and
`lathe trace` closes the loop. The whole process is a named workflow: `lathe flow sdlc`.
```
$ python lathe.py sdlc "a CLI tool that watches a folder and mirrors new files" --out qa/
RTM gate: PASS — 21 traced items -> qa/REQUIREMENTS.md (+ rtm.json)
```

## Maintenance — keep the tree pristine + file issues

### `lathe clean [--dry]`
Bring the tree to a **pristine** state, git-independently: quarantine unparseable/corrupt files to `_archive/`,
cap the failure bank. `--dry` previews.

### `lathe checkin [-m "msg"] [--push]`
**Gated check-in** — extends the pristine model to the remote so local *and* remote stay clean and in sync. It
**refuses** to commit/push unless the standing gates are green, the tree has **no relics** (caches, logs,
`_fn_fails`, journals), and you're **not behind** the upstream; otherwise it lists the blockers. `-m` sets the
message; `--push` also pushes (a secret scan runs first, and it's skipped safely if no upstream is configured).
Decision logic is harness-built (`tools/checkin_logic.py`).
```
$ python lathe.py checkin -m "add feature X" --push
checkin BLOCKED — tree/remote not pristine:
  - relics: 2
  relics: tools/__pycache__/x.pyc, build.log
  (fix: run `lathe clean`, get the gates green, or pull the remote — then retry)
```

### `lathe report "<title>"` / `lathe issues`
`report` files an issue into the shared queue (`~/.lathe/issues`) for the maintainer; `issues` is the
maintainer's triage view. Bug reports should include the run log (`lathe logs <id>`).

---
*This reference is kept honest by a docs-drift check (`qa/docs_drift_gate.py`): every command in the CLI's
table must appear here, or the gate fails. Docs can't silently fall behind the code.*
