I have enough grounding. Here is the adversarial critique and hardened spec.

---

# Adversarial critique + hardened spec — `enhancement` invocation

## 0. Ground-truth reality check (the implementer must know what is real vs. aspirational)

I verified against the live tree (`HEAD 07bbd6a`, `projects/agentic-harness/tools/workflows.py`, `lathe.py`, `flow_report.py`, `docs/GATES_REFERENCE.md`). Four load-bearing pieces of the proposed workflow **do not exist yet** and several that do exist are **bypassable**:

- **No manifest anywhere.** `grep -rn manifest --include=*.py` → zero hits. Phase-5 is 100% unbuilt. Nothing emits, nothing validates, nothing forces emission.
- **The spine is opt-in, not enforced.** `lathe flow enhancement --run` exists (`lathe.py:896`), but bare `lathe build`/`lathe review` route **around** it — they call `cmd_build`/`cmd_review` directly from the dispatch table (`lathe.py:1701-1702`). The core design claim ("bare commands route THROUGH their contract") is currently **false**.
- **`YOU` steps are printed no-ops.** `cmd_flow` prints a `you` step and appends status `'todo'` (`lathe.py:930-932`); `workflow_verdict` returns `PASS` as long as nothing is `'blocked'` — `'todo'` never blocks (`flow_report.py:20-31, 95-113`). **Every judgment step in the workflow — scope (1a), design/kinds (5), docs (12) — is currently satisfied by doing nothing.** This is the single biggest vacuity hole.
- **No adversarial-synthesis command and no sibling-regression gate exist.** `grep` for `synth`/`sibling`/`no_regress` → nothing. Steps 9 and 10 have no backing code; the step-0 `pins_digest` snapshot has nowhere to be diffed.

Everything below assumes these get built; the point of the critique is that they must be built **fail-closed**, because the gate reference itself documents that most build-time gates **no-op when there is "nothing to judge"** (mutation with 0 mutants, test-kind with 0 declared kinds, regression-proof on brand-new functions, assumption-gate under `off` policy). Those no-ops are the vacuous-pass surface.

---

## 1. Hole table — every skip / null / vacuous-pass, with the deterministic close

### Structural (the spine itself)

| # | Hole (how it's skipped / faked) | Deterministic check that closes it |
|---|---|---|
| S1 | **Bypass the contract entirely** — run `lathe build <plan>` directly; none of steps 0–14 fire, no manifest. | Dispatcher `main()` wraps the contract-bearing verbs (`do/build/review/enhancement/sdlc/checkin`) in a **run-context constructor** that mints `run_id`, runs the spine, and emits the manifest in a `finally`. Bare command == flow entry; there is no non-spine path to `cmd_build`. Plus a **standing gate** (`qa/manifest_gate.py`): any commit whose `.pins.json` changed **must** have a `docs/ce/<run_id>.manifest.json` referencing that commit — a pin-changing commit with no manifest fails the tree. This closes bypass at both entry and tree level. |
| S2 | **`YOU` step produces nothing** and the run still passes (current `'todo'`→PASS behavior). | A `you` step declares a **required output artifact** (scope record, `decisions.md`, kinds map, docs example). `classify_step` returns `'blocked'` (not `'todo'`) when the artifact is absent or fails its schema validator. `workflow_verdict` treats an unsatisfied **required** `you` step as fail. In autonomous mode the analyst call's output is fed straight to that validator; the model cannot advance by emitting prose. |
| S3 | **Manifest emitted but incomplete/vacuous** (nulls, empty arrays, all-zero cost/timing, all-true booleans). | A **manifest-completeness gate** (§4) runs before `outcome` is finalized: per-field non-vacuity rules + cross-field invariants. A manifest failing it is itself a `refuse`. |
| S4 | **Manifest not emitted on early abort/refuse.** | Emission is in the `finally` of the run context. The manifest schema requires `phase_reached` and `blocking_step`; a refuse manifest is *valid* only if it names the step that blocked (see I-2). |

### Phase 0 — Intake

| # | Hole | Close |
|---|---|---|
| I0a | **Empty sibling set → step-10 regression is vacuous** (nothing to regress). | Snapshot defines siblings by a **deterministic rule** (glob `plans/*.py` under resolved `target_dir`, minus the plan(s) being built) and records the **count**. If count==0, that is recorded and step 10 must assert "no siblings existed at intake" — never a silent pass. Manifest cross-checks `no_regression.siblings_checked` against the snapshot set (I-9). |
| I0b | **Dirty working tree at intake** → `git_rev` snapshot is not reproducible; later "byte-identical" claims are meaningless. | Intake records `git_status_clean: bool`. Under the contract, a dirty tree at intake **refuses** (or requires explicit `--allow-dirty`, which is recorded in the manifest and blocks release at step 13). |
| I0c | **`pins_digest` snapshot of empty/absent pins** silently disables the regression diff. | Snapshot records `pins_count`; the completeness gate requires `pre_state.pins_digest` to be the SHA-256 of a canonicalized, non-empty pin set **or** an explicit `pins_count:0` flag that step 10 honors. |

### Phase 1 — Front-end

| # | Hole | Close |
|---|---|---|
| F1 | **Scope record is a placeholder** — `boundary:"harness"`, `rationale:""`. Passes 1b. | Schema validator: `boundary ∈ {harness,project}`; `target_dir` must **exist or be creatable under the root implied by boundary** (harness→`engine`/core; project→`projects/<name>/plans/`) and the validator **cross-checks target_dir against boundary** (a `harness` boundary pointing into `projects/` fails). `rationale` ≥ N chars and must cite the vendoring criterion. Recorded verbatim. |
| F2 | **Acceptance criteria "empty or trivial"** — one line "it works" passes 1b. | 1b requires ≥ K atomic criteria; **each criterion must later bind to a TS id** (enforced transitively by the RTM gate at step 4). A criterion with no downstream TS fails RTM, so a trivial criterion can't survive to release. |
| F3 | **Assumption ledger is empty** (auditor "finds nothing") → assumption-gate passes with zero scrutiny. This is real: the gate only judges what the auditor surfaces (`GATES_REFERENCE §1.8` known limit). | Fail-closed: the ledger must be **non-empty**, OR carry an explicit `no_material_assumptions` attestation that **enumerates the surface checked** (encoding/rounding/ordering/empty-input/error-mode). An empty ledger with no attestation refuses. Materiality already fails-closed on mislabels (`assumption_logic`, v2.9.0). |
| F4 | **HIGH item "resolved" with a blank decision.** | Per-item validator: `materiality=="high"` ⇒ `resolution ∈ {accept,alternative,intent}` **and** `decision` non-empty **and** `recorded_in` file exists on disk and contains the verbatim decision. |
| F5 | **Scrutiny lowered via env** (`LATHE_ASSUMPTION_POLICY=high` while a `med` item is material) to dodge blocks. | The **policy level actually used** is recorded in the manifest; STRICT forces the gate on. `med`/`all` required at `high` thinking-level (thinking→scrutiny mapping is code, not user-overridable downward within the contract). |

### Phase 2 — Selection

| # | Hole | Close |
|---|---|---|
| SEL1 | **Count collapses to 1** (just correctness) → `adversarial-reviewer` never fires, defeating step 9/11. | Per-phase **floor in code**: chosen must ⊇ `{correctness-reviewer}` for review and `{adversarial-reviewer}` is mandatory for phase-4 regardless of thinking level. Casual lowers the *tail*, never the floor. |
| SEL2 | **`explore_slot: null` always** → the explore/exploit mechanic is dead; tail personas never earn grades. | At medium+ thinking, if any unused/low-sample persona exists, `explore_slot` **must be non-null**; `null` is only valid when the catalog has no eligible explore candidate (asserted against the usage ledger, recorded). |
| SEL3 | **Personas selected but never run** — `chosen[]` recorded, no contributions produced. | Completeness invariant I-3: every persona in `selection.chosen` **must** have a row in `adversarial.code_review[]` with the reviewed diff hash and either findings or an explicit `ran, 0 findings` with the diff hash as evidence. Chosen-but-silent = refuse. |

### Phase 3 — Work

| # | Hole | Close |
|---|---|---|
| W1 | **Zero new FRs** — build a plan directly, skip `sdlc`; RTM passes vacuously on an empty new-requirement set. | Enhancement contract **requires ≥1 new FR** whose id ∉ the pre-state requirement set (diffed against a snapshot of the requirement tree taken at step 0). No new FR ⇒ refuse ("an enhancement adds public surface; it must trace"). |
| W2 | **FRs authored but not linked to the built functions** — RTM only checks `CRITERIA` present + link well-formedness, not that new FRs map to `plans_built` functions. | Extend RTM: **every new FR → TS → a function present in `build.pins_written`**, and **every new function → back to a new FR**. Orphan new function or orphan new FR = fail. |
| W3 | **No property/roundtrip kind declared** → test-kind gate no-ops (`GATES_REFERENCE §1.6`, "no required kinds → nothing to enforce"). | A function tagged as a **capability function** (i.e., realizes a new FR) must declare `kinds ⊇ {property}` OR `{roundtrip}`, or carry a recorded justification. A capability function with empty `kinds` is refused **before** the model call. |
| W4 | **Capability logic smuggled into GLUE/ARTIFACTS** to dodge FUNCTIONS-level gates (mutation/kind/spec-lint). | `gate-the-glue` already refuses >2 glue lines w/o INTEGRATION and STRICT refuses ARTIFACTS-only; **additionally** require that each new FR's TS binds to a **FUNCTIONS** unit (not glue/artifact), so the capability's logic sits where the per-function gates apply. |
| W5 | **`LATHE_TRIES` actually 1** while the manifest claims `tries:3`; **wrong plan built** (a trivial sibling). | Manifest records the **actual** `tries` and `best_of_n_winner` read from the engine run log, not a literal. `plans_built` paths must be **under `scope.target_dir`** (cross-checked). |
| W6 | **`lint-spec` run on the wrong plan** (a strong sibling) to green a weak new one. | `lint-spec` target is bound by the runner to `plans_built`; the manifest's spec-lint evidence carries the plan digest, cross-checked against `build.plans_built`. |

### Phase 4 — Adversarial gate

| # | Hole | Close |
|---|---|---|
| A1 | **Ordering bug: adversarial synthesis (step 9) runs AFTER build+pin (step 7).** The stated guard "refuse to pin if synthesis produced no cases" is unenforceable — pinning already happened. | **Reorder / two-phase build.** Synthesis runs *before* the pinning build (cases folded into the plan's tests, then STRICT build pins the code that survives them), **or** step 7 pins provisionally and a **mandatory gated rebuild after step 9** re-pins; the pin the manifest attests is the post-synthesis one. Deterministic guard: `pins_written` timestamp/commit must be **≥** synthesis completion. |
| A2 | **Synthesis vacuous** — `generated:0` or `generated:N, added:0` (all "duplicates"). | Fail-closed: `generated > 0` required; `added ≥ floor` (thinking-scaled, floor≥1). Each **added** case must (a) be structurally distinct from existing tests, (b) have **failed on a mutant or a trivial stub or hit a previously-uncovered branch** (evidence recorded), and (c) pass on the final code. Cases that don't kill anything don't count toward the floor. |
| A3 | **Sibling regression vacuous** — empty sibling set (I0a), or only the touched plan is rebuilt so siblings are never actually exercised. | Step 10 **replays every sibling from pins (0 model calls)** and asserts byte-identical; a sibling that no longer builds = fail. If the intake sibling set was empty, that's asserted explicitly, not passed silently. |
| A4 | **Can't distinguish an intended shared-function change from a regression** — any pin diff could be waved through. | Deterministic invariant: the set of pin keys whose SHA changed **must be a subset of the functions in `plans_built`**. **Any** changed pin outside `plans_built` = regression fail. This is the enhancement-defining guard, expressed as set-containment (I-5). |
| A5 | **Review folds nothing** — reviewer claims a real finding + `folded_into_plan:<path>` but the plan is untouched and "rebuild" is a 0-model-call pin replay. | For every finding with `disposition:"real"`: the owning plan's **content hash must differ** pre- vs post-fold, the rebuild must show **model_calls>0** for that plan, and the finding's **reproducing test must be present** in the rebuilt plan. Real-finding count > 0 with unchanged plan digest = refuse. |
| A6 | **Hand-edit escape** — fix the generated module directly instead of folding upstream. | After review, **every generated module must byte-match its pin** (i.e., match what the current spec regenerates). An orphan hand-edit (module ≠ pin) fails the pristine/pins reconciliation. This operationalizes "never hand-edit generated code." |
| A7 | **Findings faked as "verified"** without adversarial-verify actually running. | Each finding carries `verified:bool` **plus** the verifier's evidence (the probe that killed or confirmed it). `verified:true` with no evidence blob = treated as unverified → cannot be dispositioned `real`/folded. |

### Phase 4 (cont.) — Docs & Release

| # | Hole | Close |
|---|---|---|
| D1 | **Docs "example" is non-runnable** — the docs-drift gate only checks the command *name* appears in `LATHE_COMMANDS.md` (`undocumented_commands`), so a name + one prose line passes. | Harden `docs_drift_gate`: for a **new** command, require a fenced example block **and execute it** (or bind it to a CLI-matrix/doctest case that runs in `run_gates`). `docs.example_runnable` in the manifest must be backed by an **execution record**, not a boolean literal. |
| D2 | **New command not registered** in the dispatch table or capability registry → registry_gate divergence, or command invisible. | Require the new verb present in `lathe.py`'s dispatch `table` (AST-checked) **and** a `live` entry in `capabilities.json` (registry_gate already audits one-canonical-live; make the enhancement contract assert the new capability is registered). |
| R1 | **Release with a stale/duplicate tag** — `released:true` but `canonical_tag` equals the pre-state latest tag; nothing new shipped. | `artifact.canonical_tag` must be **new** (≠ pre-state latest tag, recorded at step 0) and point at a commit whose tree contains the new pins. |
| R2 | **Manifest is step 14 (after release)** — if release aborts, no manifest; and a release can be tagged whose manifest is later found incomplete. | Manifest emission wraps the whole run (`finally`). **Sequence:** emit provisional manifest → run completeness gate → **only then** tag. Release is gated on `manifest_complete==true`. The standing `manifest_gate` (S1) then guarantees the tagged commit has a complete manifest. |

---

## 2. Hardened workflow (ordered, typed, with the guard each step carries)

```
0  INTAKE      AUTO  Mint run_id; snapshot {git_rev, git_status_clean, latest_tag,
                     requirement-tree set, sibling-plan set (+count), pins_digest (+count)}.
                     GUARD: refuse if tree dirty and not --allow-dirty (recorded).
1a FRONT-END   YOU*  Scope record {boundary,target_dir,rationale}. GUARD(1b): schema-valid,
                     target_dir⇄boundary consistent, ≥K acceptance criteria. Unsatisfied ⇒ blocked (not todo).
1c FRONT-END   AUTO  assume {plan}: ledger non-empty OR no-material attestation w/ enumerated surface;
                     every HIGH resolved w/ verbatim decision in <plan>.decisions.md. Record policy used.
2  SELECTION   AUTO  Grade-weighted pick. FLOOR: {correctness} for review; {adversarial} mandatory phase-4.
                     explore_slot non-null at medium+ if an eligible candidate exists. Record considered+chosen+why.
3  WORK        AUTO  sdlc {goal}: ≥1 NEW FR (id ∉ pre-state set); FR→TS→FUNCTIONS-unit; new-fn⇄new-FR.
4  WORK        GATE  RTM: no orphans/dangling AND new-FR↔new-function bijection holds.
5  WORK        YOU*  Design pure FUNCTIONS; capability fns declare kinds ⊇ {property|roundtrip}.
                     GUARD: empty kinds on a capability fn ⇒ blocked before model call.
6  WORK        AUTO  ack {plan}  (digest-bound; editing a test re-arms).
7a ADVERSARIAL AUTO  Synthesis FIRST: generate break-cases, fold ≥floor distinct killing cases into tests.
                     GUARD: generated>0; added≥floor; each added case kills a mutant/stub or covers new branch.
7b WORK        AUTO  LATHE_STRICT=1 build {plan}, best-of-N. Pins the code that survives 7a.
                     Record ACTUAL tries + winner. plans_built ⊆ target_dir.
8  WORK        AUTO  lint-spec {plans_built} (bound to built plans; digest cross-checked).
9  ADVERSARIAL GATE  No-regression: replay ALL siblings from pins (0 model calls), byte-identical.
                     GUARD: changed-pin-keys ⊆ plans_built functions; else regression fail.
                     Empty sibling set asserted explicitly.
10 ADVERSARIAL AUTO+YOU  review auto {files}: run chosen personas → adversarial-verify (evidence required)
                     → triage → fold each REAL finding upstream (plan digest MUST change, rebuild model_calls>0,
                     reproducing test present) → rebuild. GUARD: generated modules byte-match pins (no hand-edit).
11 ADVERSARIAL YOU*  Document: new command example, RUNNABLE (executed / CLI-matrix bound). Register in table + registry.
12 ADVERSARIAL GATE  Release gate: all build+standing gates green (incl. hardened docs-drift, registry, pristine,
                     stale, env-drift) AND tree pristine AND tag is NEW. 
13 MANIFEST    AUTO  Emit provisional manifest → completeness gate (§4) → THEN checkin + re-cut canonical + NEW tag.
14 MANIFEST    AUTO  Finalize manifest (finally-block; written on ANY prior refuse/abort with phase_reached + blocking_step).
```
`YOU*` = autonomous-mode analyst call whose structured output is gated; missing/invalid output ⇒ `blocked`, never `todo`.

Note the two material reorderings vs. the proposal: **synthesis moved before the pinning build** (closes A1), and **manifest completeness gate moved before the release tag** (closes R2).

---

## 3. Hardened guards (all in deterministic code, non-bypassable)

1. Bare `lathe enhancement|build|review …` routes through the run context; there is **no** path to the work that skips front-end/selection gates or the manifest `finally`. (S1)
2. A `you`/`YOU*` step with absent or schema-invalid output is `blocked`, and `workflow_verdict` fails on any unsatisfied required judgment step. (S2)
3. Refuse to advance past front-end if scope is undecided/invalid **or** target_dir⇄boundary mismatch **or** < K acceptance criteria. (F1, F2)
4. Refuse to build while any HIGH assumption is unresolved **or** the ledger is empty with no enumerated no-material attestation. (F3, F4)
5. Refuse to build if no new FR exists, or any new FR/new function is an orphan. (W1, W2)
6. Refuse to pin unless synthesis ran, `generated>0`, and `added≥floor` of *killing* cases — enforced **before** the pinning build. (A1, A2)
7. Regression fail if any changed pin key ∉ `plans_built`, or any sibling fails byte-identical replay. (A3, A4)
8. Review: a `real` finding requires a changed plan digest + a rebuild with model_calls>0 + a reproducing test; all generated modules must byte-match their pins (no hand-edit). (A5, A6)
9. Refuse release on any red gate, non-runnable/unregistered new command, dirty tree, or a tag equal to the pre-state latest. (D1, D2, R1)
10. Manifest emitted on every path; **release is gated on `manifest_complete`**; a pin-changing commit with no complete manifest fails a standing gate. (S3, S4, R2)
11. The enhancement skill is data — editable — but cannot disable the spine, the gates, or the manifest emit.

---

## 4. Hardened manifest — required fields + the completeness gate

Keep the proposed schema; **add** the fields below and enforce it with a deterministic **manifest-completeness gate** (`tools/manifest_complete.py`, pinned) that runs before `outcome` finalization.

**Added / changed fields**

- `schema_version`, `phase_reached`, `blocking_step` (step id or null), `manifest_complete: bool`.
- `intake.pre_state`: add `git_status_clean`, `latest_tag`, `requirement_set_digest`, `pins_count`, `sibling_count`.
- `front_end.assumptions[]`: add `policy_used`, and `attestation` (enumerated surface) when the ledger is empty.
- `selection`: add per-persona `ran: bool` and `diff_hash`; `explore_slot_reason`.
- `work.build`: `tries_actual`, `best_of_n_winner`, `plans_built[]`, `pins_written{fn→sha}`, `pins_replay: bool`.
- `work.sdlc_trace`: `new_frs[]` (each with `is_new: true`), `fr_to_fn[]` bijection map.
- `adversarial.synth_cases`: add `added[]` each with `kill_evidence` (mutant/stub/branch), `distinct: true`.
- `adversarial.no_regression`: `changed_pin_keys[]`, `changed_keys_subset_of_built: bool`, `siblings_replayed[]`.
- `adversarial.code_review[].findings[]`: `verified`, `verify_evidence`, `disposition`, `plan_digest_before/after`, `reproducing_test`, `rebuild_model_calls`.
- `docs`: `example_execution_record` (exit code / matrix id), `registered_in_table`, `registered_in_registry`.
- `outcome.artifact`: `canonical_tag` (must ≠ `pre_state.latest_tag`), `commit`.

**Per-field non-vacuity rules** (gate rejects the manifest otherwise): no required field null/empty; `timing.total_ms > 0` and ≈ Σ`per_phase_ms`; `cost.model_calls > 0` unless `pins_replay==true`; `tokens>0 ⇔ model_calls>0`.

**Cross-field invariants** (the heart of the completeness gate):

- **I-1 (pass ⇒ everything green):** `outcome.verdict=="pass"` ⇒ every `gates[].verdict=="pass"` ∧ `no_regression.verdict=="pass"` ∧ `synth_cases.all_pass ∧ generated>0 ∧ len(added)≥floor` ∧ `docs.example_runnable` ∧ `released==true` ∧ `artifact.canonical_tag != pre_state.latest_tag` ∧ `artifact.commit` set.
- **I-2 (no refuse without a cause):** `verdict=="refuse"` ⇒ `refuse_reason` non-null ∧ `blocking_step` set ∧ that step/gate appears in the record with a fail verdict.
- **I-3 (no silent personas):** `selection.chosen ⊇ {correctness-reviewer, adversarial-reviewer}` ∧ every chosen persona has a `code_review[]` row with `ran:true` and a `diff_hash`.
- **I-4 (real surface):** `new_frs` non-empty ∧ each `is_new` (id ∉ `requirement_set_digest` source) ∧ every key in `pins_written` traces to some new FR via `fr_to_fn`.
- **I-5 (regression containment):** `changed_pin_keys ⊆ pins_written.keys` (functions in `plans_built`) ∧ `changed_keys_subset_of_built==true`.
- **I-6 (assumptions):** every `materiality=="high"` item has `resolution` ∧ non-empty `decision` ∧ existing `recorded_in`; empty ledger requires `attestation`.
- **I-7 (real findings are folded, not hand-edited):** every `disposition=="real"` finding has `plan_digest_before != plan_digest_after` ∧ `rebuild_model_calls>0` ∧ `reproducing_test` present; and no generated module diverges from its pin.
- **I-8 (synthesis precedes pin):** `pins_written` commit/time ≥ synthesis completion.
- **I-9 (sibling honesty):** `no_regression.siblings_checked == intake.sibling set`; if `sibling_count==0`, `siblings_checked==[]` **and** a `no_siblings: true` flag is set (not an implicit pass).
- **I-10 (cost/timing real):** as above; a `pass` with `model_calls==0` is valid only if `pins_replay==true`.

A manifest that fails any invariant is itself an `outcome.verdict:"refuse"` with `refuse_reason` naming the invariant — and, per R2, the release tag is never cut. The standing `manifest_gate` then guarantees at the tree level that no pin-changing commit ships without a manifest passing all of I-1…I-10.

---

## 5. The three highest-leverage fixes (if the implementer does nothing else)

1. **Make `YOU` steps fail-closed** (S2) — today they are printed and the run passes; every judgment step is currently vacuous.
2. **Build the manifest emitter + completeness gate as the run-context `finally` + a standing gate** (S1/S3/S4/R2) — it doesn't exist, and it's both the priority deliverable and the thing that makes bypass detectable at the tree level.
3. **Reorder synthesis before the pinning build and express no-regression as `changed_pins ⊆ plans_built`** (A1/A4) — these two turn "adversarial gate" and "don't break siblings" from prose into arithmetic the dispatcher can enforce.