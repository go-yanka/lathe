# Lathe Workflow Reference — Harness Edition

*Authored by the harness's analyst, through the harness's own method: doctrine-primed, source-grounded
(every claim traces to a file:line I read in the live tree at v2.18.0), and multi-lens self-reviewed before
shipping. This is a reference to the 21 named workflows, the operating-contract spine that routes a bare
command through one of them, the gates that fire, the personas involved, the config you can tune, and the
concrete artifact each run leaves behind.*

Source of truth for this document:
- `projects/agentic-harness/tools/workflows.py` — `WORKFLOWS` (21), `CONTRACTS`, `CONTRACT_FOR`.
- `lathe.py` — `run_spine` / `_dispatch` / `_run_workflow` (the spine), `cmd_flow`, `cmd_do`, `cmd_build`,
  `cmd_review`.
- `projects/agentic-harness/tools/spine_core.py` — `resolve_thinking`, `depth_env`, `contract_of`.
- `projects/agentic-harness/tools/persona_orchestrator.py` — UCB1 decider (default-on).
- `projects/agentic-harness/tools/manifest.py` — the per-invocation record.
- `docs/GATES_REFERENCE.md` + `projects/agentic-harness/qa/run_gates.py` — the gates.

---

## 1. The doctrine this document is built on

Four rules from `projects/agentic-harness/CLAUDE.md` shape everything below, and you must read the workflows
through them or they look like ordinary CI steps:

1. **Two-tier, gated.** Claude (this analyst) writes specs + tests; a cheap local model implements from the
   spec; a machine — not a person — decides what ships (`CLAUDE.md:9-16`).
2. **Spec + tests are the source of truth; code is a build output.** Accepted output is test-gated and
   **pinned** (sha256 of spec+tests+model in `tools/.pins.json`) so identical inputs rebuild from cache
   (`CLAUDE.md:14-15`).
3. **Never hand-edit generated code.** Every "fix" workflow changes the *spec* and regenerates — this is why
   `code-review`, `bug-fix`, and `sdlc` all route their fixes UPSTREAM into the owning plan
   (`CLAUDE.md:12-13`, `workflows.py:15`, `workflows.py:28`).
4. **Decide-then-archive; verify from a live probe, never memory** (`CLAUDE.md:28-29,46-47`). That last rule
   is the one I applied to myself: nothing here is stated from recall — it is stated from a file I opened.

---

## 2. The operating-contract spine (how a bare command becomes a gated workflow)

Every top-level `lathe` invocation goes through `run_spine` (`lathe.py:1760`). `main()` sends the *first*
call through the spine and any re-entrant inner call raw, guarded by an env token
(`lathe.py:1755-1757`, `_SPINE_GUARD`). The spine is deterministic CODE wrapped around workflow DATA — "a
workflow can define bad steps but cannot delete a phase" (`lathe.py:1761-1762`).

**The six phases**, as they actually execute (`run_spine`, `lathe.py:1760-1833`):

| Phase | What happens | Evidence |
|---|---|---|
| 0 · intake | Open the manifest; resolve the thinking dial → depth env stamps; record `intake` gate row | `lathe.py:1764, 1786-1793` |
| 1 · contract | `contract_of(cmd, CONTRACT_FOR)` looks up the command's contract (workflow, flags) | `lathe.py:1785`; `spine_core.py:25` |
| 2 · promotion | If the contract names a workflow (and not `--json`), load it; record `promotion` gate + `set_workflow` | `lathe.py:1800-1811` |
| 3 · work | `_run_workflow(...)` runs the workflow steps in order, else `_dispatch` runs the bare primitive | `lathe.py:1812-1814` |
| 4 · gates | If `contract["gate"]` and the write was green, run the standing suite as a real subprocess | `lathe.py:1815-1816`; `_phase_gates`, `lathe.py:1904` |
| 5 · emit | `finalize()` in a `finally` — the manifest is written UNCONDITIONALLY, even on crash | `lathe.py:1828-1833` |

**Routing.** `CONTRACT_FOR` (`workflows.py:195-216`) maps each command to `{workflow, front_end, select,
gate, writes, argmap}`. A command absent from the map (or `{}`) is **TRIVIAL**: the spine still runs
(run_id + thinking + manifest) but phases 2/4 no-op — byte-identical to the old read-only behavior
(`workflows.py:190-193`). This is why `status`, `logs`, `metrics`, `plans`, etc. are `{}`.

**One important honesty note about the flags.** `front_end` and `select` are *declared* in the contract as
metadata, but in the visible `run_spine` path only `contract["workflow"]` and `contract["gate"]` are acted
on directly (`lathe.py:1801, 1815`). The front-end interview and persona selection are realized *inside* the
primitive commands — `cmd_do` runs the autonomy liaison (`lathe.py:179`), `cmd_review auto` runs the persona
decider (`lathe.py:267-312`). So read `front_end:1`/`select:1` as "this command's primitive does a
clarify/selection step," not "the spine makes a separate call." (This was an adversarial-lens catch on my
own first draft — see §7.)

**`build`/`do` gate:0 on purpose.** The engine already runs the standing regression *inside* the build, so
the contract sets `gate:0` to avoid gating twice for zero added coverage (`workflows.py:194, 198-199`).

**The manifest (the artifact every run emits).** `Manifest` (`manifest.py`) records: intake (goal, resolved
workflow + step labels — `set_workflow`, `manifest.py:125`), per-step rows (`append_step`, `:134`), gate
verdicts (`record_gate`, `:141`), persona/lens selection (`set_selection`, `:148`), per-role token usage
(`record_usage`, `:155`), and the outcome + integrity sha256 (`set_outcome`, `:174`; `finalize`, `:183`).
It is written to `docs/ce/<run_id>.manifest.{json,md}` (`finalize` docstring, `manifest.py:184`).

**Two different manifests exist — don't conflate them.** The spine manifest above lives in `docs/ce/`. The
*persona* orchestrator writes a SEPARATE per-run manifest to
`projects/agentic-harness/agents/manifests/<run_id>.md` (`persona_orchestrator.py:50-51, 164-167`). The
"read the run manifest (docs/ce/)" YOU-steps refer to the spine one.

---

## 3. The thinking-level dial

One knob scales rigor across a whole run. `resolve_thinking(flag, env, config)` picks the level from, in
precedence order, the `--think=<level>` flag → `LATHE_THINK` env → `lathe.config.json` `thinking.level`,
defaulting to `medium` (`spine_core.py:4-11`). `depth_env(level)` expands it (`spine_core.py:13-23`):

| Level | `LATHE_TRIES` | `LATHE_SELECT_N` | `LATHE_ASSUMPTION_POLICY` |
|---|---|---|---|
| `casual` | 1 | 1 | `off` |
| `medium` (default) | 3 | 2 | `high` |
| `high` | 5 | 4 | `high+med` |

The spine applies these with `os.environ.setdefault` (`lathe.py:1790-1791`) — **env > profile > config >
default: an explicit env var you set always wins.** Runnable example: `lathe do "parse an ISO-8601 duration"
--think=high` builds best-of-5, considers 4 personas, and blocks on high+med-materiality assumptions.

> Adversarial note (verify on your machine): `high` emits the literal policy string `high+med`, whereas
> `GATES_REFERENCE.md:212-213` documents the assumption policy vocabulary as `off`/`high`/`med`/`all`. Treat
> `high+med` as "high and med both block"; confirm your `assumption_logic` parser reads it that way before
> relying on it. (Self-review catch — §7.)

---

## 4. Personas — who is "in the room" for a review

Persona selection is **on by default** (`persona_orchestrator.is_enabled()` returns `True` unless
`LATHE_PERSONA_UCB` ∈ {0,false,no,off} or config `personas.explore_exploit=false`,
`persona_orchestrator.py:21-39`). The decider is a **relevance pre-filter → UCB1 explore/exploit** over the
pool: `relevance_pool` ranks candidates by `agent_router.score_match`, then `ucb1(grade, visits, total, c)`
balances exploration of unseen personas against exploitation of high-graded ones (`select_live`,
`persona_orchestrator.py:96-135`). Grades are recomputed from the usage ledger after each run
(`update_grades`, `:176-211`) — verified findings raise a persona's grade.

For a **review**, the lens set is: the floor `["correctness", "adversarial"]` (`_DEFAULT_LENSES`,
`lathe.py:257`), PLUS up to 2 domain specialists the decider picks from the code sample
(`security`/`reliability`/`performance`/`data`/`api`/`maintainability`/`testing`,
`lathe.py:278-288`), PLUS any config-mandatory personas (`persona_overrides`, `lathe.py:289-295`), PLUS any
license-gated expert auto-spawned for a domain the vendored set doesn't cover (`auto_spawn_for_goal`,
`lathe.py:300-305`). The full lens vocabulary is `_ALL_LENSES` (`lathe.py:256`): security, correctness,
adversarial, data, perf, reliability, api, maintainability, testing, ui. The resolved selection is recorded
to the manifest (`set_selection`, `lathe.py:309-312`).

---

## 5. The gates

Two families (`GATES_REFERENCE.md:7-16`).

### 5.1 Build-time rigor gates — off by default, composed by `LATHE_STRICT=1`

The floor is always on; the seven rigor toggles are opt-in and `LATHE_STRICT=1` turns them all on with sane
defaults (`GATES_REFERENCE.md:28-38`, expanded at `engine_v2.py:98`). STRICT also *clamps* a weaker pre-set
back up — you can go stricter, never weaker (`GATES_REFERENCE.md:333-339`).

| Gate | Env var | STRICT default | Refuses when |
|---|---|---|---|
| **Acceptance** (floor, always on) | `LATHE_SANDBOX`, `LATHE_TRIES` | — | a spec test fails in the sandbox (`GATES_REFERENCE.md:39-59`) |
| **Traceability** | `LATHE_STRICT` + plan `CRITERIA` | on | a FUNCTIONS plan declares no `CRITERIA` (`:61-81`) |
| **Regression-proof** | `LATHE_REGRESSION_PROOF` | `1` | every new test passes on the OLD code (`:84-97`) |
| **Spec-lint** | `LATHE_LINT_SPEC` | `block` | a trivial stub passes all the tests (`:99-118`) |
| **Mutation-score** | `LATHE_MUTATION_SCORE` | `0.5` | `killed/total` below threshold (`:121-144`) |
| **Test-ack** | `LATHE_TEST_ACK` | `1` | tests not acked, or edited since ack (`:147-158`) |
| **Test-kind** | `LATHE_TEST_KIND` + `kinds` | `1` | a required test kind is absent (`:161-178`) |
| **Gate-the-glue** | `LATHE_GATE_GLUE`, `LATHE_GLUE_MAX` | `1` | glue > max lines with no INTEGRATION test (`:181-197`) |
| **Assumption** | `LATHE_ASSUMPTION_GATE`, `LATHE_ASSUMPTION_POLICY` | `1`, `high` | a material assumption is unconfirmed (`:200-220`) |

### 5.2 Standing regression gates — always on, run after every green build

`qa/run_gates.py` runs these; any non-zero exit makes the whole build RED (`GATES_REFERENCE.md:224-238`).
**The live suite is 10 gates** (`run_gates.py:24-33`), not the 7 that `GATES_REFERENCE.md:230-238` tabulates
— the reference doc is stale by three (a docs-drift finding I raise in §7):

1. `tree_no_stale_dups` (`stale_gate.py`) — no backup/dup/superseded file in `tools`/`plans`.
2. `no_duplicate_resources` (`resource_dups_gate.py`) — one canonical DB per basename.
3. `capability_registry` (`registry_gate.py`) — one `live` implementation per capability.
4. `pristine_tree` (`pristine_gate.py`) — every `.py` parses.
5. `lint_no_real_bugs` (`lint_gate.py`) — ruff `F`/`E9`, skips cleanly without ruff.
6. `docs_not_drifted` (`docs_drift_gate.py`) — every command documented WITH an example.
7. `env_not_drifted` (`env_drift_gate.py`) — every env var the code reads is in `env_catalog.py`.
8. `manifest_contract` (`manifest_contract_gate.py`) — every invocation emits a complete, un-skippable
   manifest (`run_gates.py:31`).
9. `spine_enforced` (`spine_gate.py`) — guard-forge / skill-subprocess / bypass attacks defeated
   (`run_gates.py:32`).
10. `gate_tristate` (`tristate_gate.py`) — gates fail CLOSED (INOPERATIVE), never open, on their own error
    (`run_gates.py:33`).

---

## 6. The 21 workflows

`lathe flow` lists them; `lathe flow <name>` shows the ordered steps + the contract (when/entry/deliverable/
done) BEFORE you run; `lathe flow <name> --run [targets]` executes the AUTO/GATE steps in order, halting on a
blocked step, and prints YOU steps as checkpoints (`cmd_flow`, `lathe.py:919-976`). Step types:
`auto` = a runnable `lathe` subcommand (gated on success), `gate` = the standing suite, `you` = a human/
analyst judgment checkpoint (never auto-run) (`workflows.py:8-13`).

### 6.1 The six named, end-to-end workflows

These carry a full CONTRACT (`workflows.py:100-132`) and are meant to be run with `lathe flow <name> --run`.

#### `code-review` — land ONLY verified fixes
- **Invoke:** `lathe flow code-review --run tools/foo.py tools/bar.py`
- **When/entry/deliverable/done** (`workflows.py:101-105`): a change is ready and you want only verified
  fixes landed; the files build and you know their owning plan; real findings folded UPSTREAM + rebuilt +
  gated; done when gates green, touched specs pass `lint-spec`, canonical re-cut if shipped.
- **Steps** (`workflows.py:24-30`):
  1. [AUTO] `review auto {files}` — the decider picks reviewer personas, then reviews. **Personas:**
     correctness+adversarial floor + up to 2 domain specialists + auto-spawned experts (§4). **Artifact:**
     manifest `selection` block + `docs/ce/` review manifest.
  2. [GATE] verify the tree — the 10 standing gates (§5.2).
  3. [YOU] triage real findings vs false positives; write the fix for each real one.
  4. [YOU] fix UPSTREAM — fold each finding into the owning plan and `lathe build <plan>`; never hand-edit.
     *(The comment at `workflows.py:21-23` documents why this is a YOU row: a bare `review <files>` target
     must not be mis-bound as a plan.)*
  5. [YOU] if shipped, re-cut canonical immediately.
- **Config:** `LATHE_PERSONA_UCB`, config `personas.priority`/`mandatory`; `--think` scales `LATHE_SELECT_N`.

#### `bug-fix` — reproduce → diagnose → fix the SPEC → verify → review → release
- **Invoke:** `lathe flow bug-fix --run plans/my_plan.py`
- **Contract** (`workflows.py:106-110`): a build/behavior is wrong and you need it fixed at the source;
  entry is you can name + reproduce the failing plan; deliverable is the SPEC/tests pin correct behavior +
  green rebuild + reviewed.
- **Steps** (`workflows.py:34-44`):
  1. [AUTO] `build {plan}` — reproduce (captures a run log).
  2. [AUTO] `logs --tail` — read the full run trace: spec bug or impl bug?
  3. [AUTO] `lint-spec {plan}` — are the tests even good? (a trivial impl must not pass them — the spec-lint
     gate, §5.1).
  4. [YOU] fix the SPEC/tests to pin correct behavior, then rebuild — never hand-edit.
  5. [AUTO] `assume {plan}` — **assumption audit**; HIGH-materiality blocks (the assumption gate, §5.1).
  6. [AUTO] `build {plan}` — rebuild under STRICT; the fix must ship a test that reproduces the bug
     (**regression-proof gate**, §5.1).
  7. [GATE] verify tree clean + no regression.
  8. [AUTO] `review auto {files}` — decider picks personas.
  9. [YOU] resolve the issue + re-cut canonical.
- **Artifact:** run log (`logs`), `<plan>.decisions.md` (from `assume`), rebuild pins in `.pins.json`,
  review manifest.

#### `enhancement` — build a NEW capability the disciplined way
- **Invoke:** `lathe flow enhancement --run plans/new_cap.py`
- **Contract** (`workflows.py:111-115`): you want a new capability, dogfooded through the harness; entry is
  the idea is scoped as harness-vs-project (vendoring boundary).
- **Steps** (`workflows.py:48-58`):
  1. [YOU] scope it: general HARNESS capability or PROJECT-specific check? (vendor-don't-fork).
  2. [YOU] design small PURE functions + strong tests; declare required test `kinds` per function — a
     property invariant needs a `property` test (the **test-kind gate** refuses a missing declared kind under
     STRICT, §5.1).
  3. [AUTO] `assume {plan}` — assumption audit (HIGH blocks).
  4. [AUTO] `build {plan}` under STRICT — criteria + ack + stub-proof + change-proof + assumption-gate.
  5. [AUTO] `lint-spec {plan}` — confirm tests pin behavior.
  6. [GATE] integrate + verify the whole tree.
  7. [AUTO] `review all {files}` — **all** lenses (note: `all`, not `auto` — every lens in `_ALL_LENSES`).
  8. [YOU] document it WITH an example (the **docs-drift gate** enforces this, §5.2).
  9. [YOU] re-cut canonical.
- **Artifact:** pinned module, `.decisions.md`, all-lens review manifest, updated `LATHE_COMMANDS.md`.

#### `doc-review` — prove docs haven't drifted from the code
- **Invoke:** `lathe flow doc-review --run docs/GATES_REFERENCE.md`
- **Contract** (`workflows.py:116-120`): docs/plans checked for accuracy and proven not-drifted.
- **Steps** (`workflows.py:62-66`):
  1. [AUTO] `review maintainability {files}` — the doc-review lens.
  2. [GATE] **docs-drift gate** — every CLI command documented with an example, or the build fails.
  3. [YOU] fix gaps; keep every example runnable.
- **Artifact:** review manifest + a green docs-drift verdict. *(This document is itself a doc-review
  deliverable — and applying it caught the stale 7-vs-10 gate table, §7.)*

#### `sdlc` — full SDLC, RTM-gated, every proof gate
- **Invoke:** `lathe flow sdlc --run "ingest a CSV and emit per-column stats"`
- **Contract** (`workflows.py:121-126`): you want the full process — requirements with IDs, traceability,
  every proof gate; entry is a goal + configured endpoints; deliverable is RTM-gated `REQUIREMENTS.md` + a
  criteria-mapped plan built under STRICT + the trace matrix.
- **Steps** (`workflows.py:70-82`):
  1. [AUTO] `clarify {goal}` — the requirements liaison interrogates you first (inputs/outputs/success/edge/
     non-goals).
  2. [AUTO] `sdlc {goal}` — author LAYERED, ID-traced requirements (UC→BR→FR→TS); the **RTM gate** refuses
     orphans/dangling refs (`sdlc_rtm.rtm_gaps`, §5.1).
  3. [YOU] review `REQUIREMENTS.md`; turn the CRITERIA block into a plan (each TS → criterion → named tests).
  4. [AUTO] `ack {plan}` — acknowledge the test set (the **test-ack gate** oracle, §5.1).
  5. [AUTO] `assume {plan}` — adversarial assumption audit; each HIGH must be DECIDED.
  6. [YOU] resolve each blocking assumption (`lathe assume {plan} --resolve`) — recorded in
     `<plan>.decisions.md`. No blanket accept.
  7. [AUTO] `build {plan}` under STRICT — criteria+ack+stub-proof+change-proof+mutation-score+assumption all
     forced.
  8. [AUTO] `trace {plan}` — emit the requirement→test→pin→model **traceability matrix** (the compliance
     artifact).
  9. [AUTO] `review auto {files}`.
  10. [GATE] tree clean + no regression.
  11. [YOU] release: checkin + re-cut canonical.
- **Artifact:** `REQUIREMENTS.md`, `<plan>.decisions.md`, the trace matrix, STRICT-build pins, manifest.

#### `new-project` (alias: `onboard-project`) — vendor Lathe and land the first gated build
- **Invoke:** `lathe flow new-project --run`
- **Contract** (`workflows.py:127-131`): onboarding a fresh project; entry is a repo + implementer/analyst
  endpoints.
- **Steps** (`workflows.py:86-93`):
  1. [YOU] vendor a pinned copy of canonical Lathe; keep your product layer separate (VENDORING.md).
  2. [YOU] configure endpoints: `LOCAL_OPENAI_URL` (implementer) + `HARNESS_CLAUDE_URL` (analyst).
  3. [AUTO] `selftest` — verify the install.
  4. [GATE] confirm the tree is clean.
  5. [AUTO] `do "a small pure helper you need"` — first build: draft a spec, build on the local model under
     gates, pin it.
  6. [YOU] add YOUR product data-quality gates (DATA_QUALITY.md).
- **Artifact:** a vendored, configured, verified install + first pinned `do` build.

### 6.2 The fifteen per-invocation workflows

These are the "operating contract #12 Phase 2" promotions (`workflows.py:135-186`): a bare command runs its
primitive verbatim (stdout + exit code preserved — the manifest is a side-file) plus only the steps that ADD
enforcement. You rarely type `lathe flow <name>`; you type the bare command and the spine promotes it. Each
entry below gives the bare invocation that triggers it.

| Workflow | Bare command | Steps (`workflows.py`) | Adds / artifact |
|---|---|---|---|
| **build-from-goal** | `lathe do "<goal>"` | AUTO `do {args}` → GATE standing → YOU read manifest (`:140-147`) | front-end clarify + persona select inside `cmd_do`; manifest in `docs/ce/` |
| **build-from-plan** | `lathe build <plan>` | AUTO `build {args}` → AUTO `trace {plan}` → YOU read manifest (`:148-155`) | engine gates internally (gate:0); trace matrix |
| **clarify-goal** | `lathe clarify "<goal>"` | AUTO `clarify {args}` (`:156-157`) | requirements-liaison interview → committed brief |
| **assumption-audit** | `lathe assume <plan>` | AUTO `assume {args}` (`:158-159`) | materiality-ranked ledger → `<plan>.decisions.md`; `gate:1` in contract |
| **verify-reproduce** | `lathe verify <plan>` | AUTO `verify {args}` (`:160-161`) | re-verify pinned bytes reproduce from the pin store |
| **gate-quality** | `lathe gate` | AUTO `gate` (`:162-163`) | the standing suite, exit-code honest |
| **trace-inspect** | `lathe trace <plan>` | AUTO `trace {args}` (`:164-165`) | requirement→test traceability report |
| **maintain-tree** | `lathe clean` | AUTO `clean {args}` → GATE standing (`:166-168`) | janitor removes stale/dup/corrupt, then proves pristine |
| **ship-release** | `lathe checkin` | AUTO `checkin {args}` → YOU tag/notes (`:169-171`) | leak-scanned check-in |
| **serve-api** | `lathe serve` | AUTO `serve {args}` (`:172-173`) | REST API v0 (runs until stopped) |
| **select-grade-experts** | `lathe agent "<need>"` | AUTO `agent {args}` (`:174-175`) | decider matches/spawns persona(s), license-gated fetch |
| **report-triage** | `lathe report` | AUTO `report {args}` → YOU triage (`:176-178`) | consuming-project issue intake |
| **autonomous** | `lathe auto` | AUTO `auto {args}` (`:179-180`) | the supervised autonomy loop (its own gates inside) |
| **sdlc-requirements** | `lathe sdlc "<goal>"` | AUTO `sdlc {args}` → YOU review REQUIREMENTS.md (`:181-183`) | RTM-gated requirements; `front_end:1, select:1, gate:1` |
| **onboard-project** | `lathe flow new-project` | YOU follow new-project (`:184-185`) | alias of new-project |

**How the promotion binds argv** (`_run_workflow`, `lathe.py:1836-1882`): the PRIMITIVE-FIRST step (the first
auto step whose command == the invoked command) re-runs your ORIGINAL argv verbatim — an identity, never a
re-template — so `lathe do "goal with spaces"` is not mangled. ENFORCEMENT steps bind `{plan}` to the first
positional arg and `{files}`/`{args}`/`{goal}` to the full arg string. A placeholder that binds to nothing is
SKIPPED, never silently passed (`lathe.py:1872-1873`). `--json` stays primitive-only (compat guarantee:
`lathe.py:1801`).

---

## 7. Self-review notes (multi-lens, applied to this document before shipping)

The harness never ships an un-reviewed first draft. I ran three lenses over my own text; here is what each
caught and how the final text changed.

**CORRECTNESS lens — is every claim traceable to code I read?**
- *Caught:* my draft asserted "7 standing gates" from `GATES_REFERENCE.md:230-238`. Verifying against the
  live runner (`run_gates.py:24-33`) showed **10** — the reference doc omits `manifest_contract`,
  `spine_enforced`, and `gate_tristate`. **Changed:** §5.2 now lists all 10 and flags the reference as stale
  (a genuine docs-drift finding, exactly the kind `doc-review` exists to surface).
- *Caught:* I nearly wrote "the spine runs a front-end phase and a selection phase" from the `front_end`/
  `select` contract flags. Reading `run_spine` showed those flags are metadata; only `workflow` and `gate`
  are acted on in the visible path. **Changed:** §2 now states the interview/selection happen inside the
  primitives, not as separate spine calls.

**DOCS lens — is every command shown with a runnable example, nothing ambiguous?**
- *Caught:* the per-invocation table originally listed workflow names without the bare command that triggers
  them, which is the whole point of the promotion machinery. **Changed:** added a "Bare command" column so
  each row is runnable (`lathe do "<goal>"`, `lathe gate`, …).
- *Caught:* `enhancement` step 7 is `review all` while every other review step is `review auto`. Easy to
  gloss. **Changed:** called out `all` vs `auto` explicitly.

**ADVERSARIAL lens — where would a reader be MISLED?**
- *Caught:* the thinking dial's `high` level emits `LATHE_ASSUMPTION_POLICY=high+med` (`spine_core.py:17`),
  a string NOT in the documented policy vocabulary (`off`/`high`/`med`/`all`). A reader could assume it's
  rejected. **Changed:** §3 flags it as "verify your parser accepts it," not stated as guaranteed-correct.
- *Caught:* "the manifest" is ambiguous — there are TWO (spine `docs/ce/` and persona
  `agents/manifests/`). A reader told to "read the run manifest" could open the wrong one. **Changed:** §2
  disambiguates both paths and says which the YOU-steps mean.
- *Caught:* a reader might try `lathe flow code-review --run <files>` expecting the rebuild to be automatic;
  steps 3–5 are YOU rows and the comment at `workflows.py:21-23` explains a bare review's file target must
  not be auto-bound as a plan. **Changed:** §6.1 quotes that rationale so the manual step reads as
  intentional, not missing.

*Every claim above is traceable to a file:line in the v2.18.0 tree I read; verify any gate or route from a
live probe, per the doctrine — never from this document's memory.*
