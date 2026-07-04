I have enough grounding in the actual shipped primitives to critique this against reality rather than against the proposal's own optimistic framing. The most important finding is that the proposal inherits three primitives (`classify_step`, `workflow_verdict`, and the two gates' skip-clean behavior) that make almost every guarantee vacuously satisfiable *today*. Here is the adversarial critique and the hardened spec.

---

# ADVERSARIAL CRITIQUE — `lathe doc-review` contract

## The three structural defects the proposal inherits (root causes)

Everything below descends from three facts in the shipped code that the proposal does not touch:

**R1 — `SKIPPED` counts as green.** Both live gates fail-*open* on their own inability to run. `qa/docs_drift_gate.py` prints `"... — SKIPPED"` and `return 0` when `lathe.py`/`LATHE_COMMANDS.md` aren't at the expected root; `qa/env_drift_gate.py` does `return 0` on any import failure, missing files, or `except Exception`. `classify_step` (in `plans/W01_flow_report.py` / `tools/flow_report.py`) sees `rc==0`, no failure-signal substring, and returns `'pass'`. So a gate that could not execute is indistinguishable from a gate that passed. This is the single biggest hole: **any of G7–G11 turns green by not running.**

**R2 — judgment steps never block.** `classify_step(kind='you', ...)` unconditionally returns `'todo'`, and `workflow_verdict` only blocks on `'blocked'` — `'todo'` is treated as PASS. Every `you`/analyst step in the proposal (A1 charter, Y5 triage, A6 routing) is therefore non-blocking by construction. The proposal's phrase "output gated by code" is not true of the primitive it builds on. There is also **no `REFUSE` in `workflow_verdict`'s codomain** — it returns only `PASS`/`BLOCKED` — so the promised REFUSE-on-unresolved-charter cannot even be expressed today.

**R3 — pass is string-sniffing, not proof-of-work.** `classify_step` for `auto` returns `'pass'` on `rc==0` unless the output happens to contain one of `['not exist','could be read','traceback','fail ::','error:']`. An `auto` step that emits **nothing** (empty output, clean exit) passes. So "a persona reviewed the corpus" and "a persona was invoked and returned empty" are the same green.

Every hole below is one of these three wearing a doc-review costume.

---

## Enumerated holes (where a step is skipped / produces nothing / passes vacuously) + the deterministic close

**H1 — Empty/degenerate corpus ⇒ whole review passes on nothing.**
If `{files}` is passed but empty/whitespace, or the default glob matches zero files (wrong cwd, everything under `_archive/`), `intake.corpus=[]`. Every persona reviews nothing, every drift probe has nothing to check (0 undocumented, 0 dangling, 0 examples), all gates green, `verdict=PASS`.
*Close:* In Phase 0 code, `assert len(corpus) > 0` → else terminal `REFUSE` with `blocking_reason="empty_corpus"`. Record `intake.corpus_count` and make the manifest-completeness gate (H15) require `corpus_count >= 1` **and** each corpus entry to have a nonzero `size_bytes` (empty files are REFUSE, not silently reviewed).

**H2 — Gates fail-open (`SKIPPED==0`) ⇒ G7/G8 green without running.** (R1)
*Close:* For a doc-review run the gates must be invoked in a **fail-closed mode**. Concretely: each probe returns a tri-state `probe_status ∈ {ran_clean, ran_found, could_not_run}` recorded in the manifest, and the flow-runner maps `could_not_run` → `BLOCKED`, never `pass`. Replace the `return 0` skip paths with `return 2` (distinct from 0=clean and 1=drift-found) and teach the runner that `rc==2` on a required probe is BLOCKED. A doc-review whose docs_drift probe can't find `lathe.py` is BLOCKED ("cannot prove non-drift"), not PASS.

**H3 — `undocumented_commands` is substring presence, not "with an example."** (vacuous claim)
`tools/undocumented_commands.py` passes any command whose bare token appears **anywhere** in `LATHE_COMMANDS.md` — a mention in prose, a changelog line, or an unrelated code fence satisfies it. The gate's docstring and the workflow's DoD both claim "documented **with a runnable example**"; the checker does not verify that. So G7 is satisfiable by a bare mention.
*Close:* Strengthen the checker to require, per command, a fenced example block whose command line invokes that token (regex over ```` ``` ```` blocks: a line matching `^\s*(lathe\s+)?<cmd>\b`). Record per command `{cmd, mentioned:bool, has_example:bool}`; G7 fails if any `mentioned && !has_example`. This is also the join point for G10.

**H4 — No reverse drift check (stale commands).**
The proposal names it (A4 "doc commands absent from `lathe.py`'s `table` → stale") but the shipped `undocumented_commands` is one-directional and `_table_commands` only extracts the table. A doc can document a command that no longer exists and pass.
*Close:* `doc_commands = {tokens matching (lathe )?<word> in fenced blocks}`; `stale = doc_commands - set(table)`. `stale != [] ⇒ rc 1`. Record `docs_drift.stale_cmds[]`.

**H5 — `env_drift` "unused" is advisory; extraction is a lower bound.**
`env_drift_gate` prints unused vars but never fails on them, and `extract_env_vars` only matches literal `os.environ.get/getenv/os.environ["X"]`. Indirect reads (`os.environ.get(name_var)`, `**os.environ`, config-driven, subprocess env) are invisible ⇒ "clean" is a floor, not a proof. A doc claiming an env var exists that the code reads indirectly won't be validated.
*Close:* Keep undocumented→fail. For doc-review specifically, add the **reverse for docs**: every env token `LATHE_*`/`HARNESS_*`/`*_URL` appearing in the corpus must be in `env_catalog.REGISTRY` (catches docs inventing/renaming a var). Record `env_drift.doc_only_vars[]`; nonempty ⇒ rc 1. Note the extraction lower-bound limitation explicitly in the manifest (`env_drift.extraction=static-lower-bound`) so a green isn't overclaimed.

**H6 — Charter default auto-satisfies G1 ⇒ assumption-gate is vacuous.**
A1 ships a **default** truth-source ranking (`code > gates > …`). G1 "refuse while ranking is unresolved" can therefore never fire — the default is always "resolved." The exemplar's live HIGH item ("is `projects/your-product` supposed to exist?") gets defaulted, not decided.
*Close:* Distinguish `resolution ∈ {defaulted, decided}` per charter item. Under `LATHE_STRICT=1`, any charter item with `materiality=HIGH` and `resolution=defaulted` ⇒ `BLOCKED`. Additionally, **derive** at least one mandatory HIGH charter item from machine facts, not the model: for every `dangling_path` and every `doc_only_var` found in A4, auto-inject a HIGH charter item that must be `decided`. This makes G1 impossible to satisfy while a machine-confirmed drift is unaddressed — the model cannot make it disappear by writing a blank charter.

**H7 — Severity is model-assigned ⇒ G11 defeated by relabeling.** (R2 + judgment laundering)
"G11: no unresolved HIGH finding remains" gates on `severity`, which the persona/model sets. The model can label every finding MEDIUM and pass G11. The adversarial gate is one prompt away from vacuous.
*Close:* Severity that gates must be **machine-derived, not model-trusted**. Define `effective_severity = max(model_severity, machine_floor)` where `machine_floor=HIGH` iff the finding is corroborated by a deterministic probe (a `dangling_path`, a `stale_cmd`, an `undocumented_var`, a failed example, a count mismatch, or an unsubstituted placeholder). G11 gates on `effective_severity`. Model can upgrade, never silently downgrade a machine-confirmed HIGH.

**H8 — `you`/analyst steps return `'todo'` ⇒ Y5 triage and A1 charter never block.** (R2)
In autonomous mode the analyst call's *output* is supposed to be gated, but the primitive returns `'todo'` (non-blocking) for kind `you`, and the manifest can be emitted with `resolution` empty and still PASS.
*Close:* In autonomous mode, a `you` step is not "todo" — its produced artifact is a gated `auto` output. Change semantics: an analyst judgment step must emit a **structured artifact** (charter.md with a resolved-ranking; triage.json with a decision per finding) and a code check validates it (schema + coverage). A `you` step with no artifact ⇒ `BLOCKED`, never PASS. Extend `workflow_verdict` codomain to `{PASS,BLOCKED,REFUSE}` and map an unexecuted required judgment step to `BLOCKED` (interactive) / `REFUSE` (charter-level).

**H9 — `example-runnability` (G10) passes on zero extracted examples.** (vacuous)
If the fence extractor finds no runnable blocks (wrong language tag, examples written without fences, or casual-mode "changed docs only" when nothing changed), `total=0, run=0, failed=[]` ⇒ green. "0 of 0 ran" proves nothing, yet is the flagship guarantee.
*Close:* Two independent counters that must reconcile: `fenced_blocks_total` (count of all ```` ``` ```` blocks) and `examples_extracted` (blocks classified runnable). Record both. G10 requires: (a) `examples_extracted > 0` **unless** `fenced_blocks_total == 0` (a corpus genuinely without examples is recorded as `n/a`, not `pass`); (b) `run == examples_extracted` (every extracted example was actually executed/dry-resolved — no silent drops); (c) `failed == []`. A drop between extracted and run ⇒ BLOCKED. Casual-mode "changed docs only" must still run G10 over the **whole corpus** for `examples_extracted` accounting, downgrading only execution, so it can't zero itself out.

**H10 — `path-liveness` (G9) under-fires ⇒ dangling paths slip; placeholders inferred not enumerated.**
The exemplar's F1 (`projects/your-product`, literal `<LATHE_ROOT>`) is exactly the kind a loose "path-like token" regex misses when the path sits in prose. Inference ("does this look like a path?") is the vacuity surface.
*Close:* Two deterministic passes. (1) **Explicit placeholder denylist** (`<LATHE_ROOT>`, `<...>`, `projects/your-product`, `a prior agent`, etc.) — literal string search, any hit ⇒ HIGH finding, no inference. (2) Path-liveness over tokens matching `[\w.-]+/[\w./-]+` that resolve repo-relative; each must `os.path.exists`. Record `path_liveness.checked_count` and `dangling_paths[]`; require `checked_count > 0` when the corpus contains any `/`-bearing token (so the extractor can't silently match nothing). G9 fails on any dangling path OR any denylist hit.

**H11 — Count/version claims (A4) unenforced-by-default.**
"143 entries", "six gates", "12 vendored", `VERSION` — the proposal lists these but no probe binds a claim string to an artifact. Left unchecked, this is the exemplar's F5 drift.
*Close:* A declared claim-map: regex patterns → resolver (`agents/catalog.json` length, count of `qa/*_gate.py`, `VERSION` file, CE persona count). `claim_checks.mismatches[]` nonempty ⇒ rc 1. Also record `claim_checks.count_claims_checked` and require it ≥ number of count-shaped tokens the extractor found (so extraction can't silently skip claims it saw).

**H12 — `ce_floor_satisfied` is a pre-set bool ⇒ true even when the lens didn't run.**
If the code sets `ce_floor_satisfied=true` at selection time but the persona body fetch/inject fails (or returns empty), the review runs blind while the flag says covered.
*Close:* Derive the flag, don't set it. `ce_floor_satisfied = ('maintainability' in ran_contributors) and ('adversarial' in ran_contributors)` where `ran_contributors` = personas whose contributor record has `status='ran'` and a non-null structured result. A selected-but-errored CE persona ⇒ `ce_floor_satisfied=false` ⇒ BLOCKED.

**H13 — Zero findings is ambiguous: "clean" vs "never ran."** (R3)
A contributor with `findings_count:0` could have examined the corpus and found nothing, or errored/timed-out/returned empty. Both currently pass.
*Close:* Per-contributor `status ∈ {ran, errored, skipped}` and `evidence = {files_examined:int, bytes_examined:int}`. A `ran` contributor with 0 findings must show `files_examined == corpus_count`. Any selected persona with `status ∈ {errored,skipped}` ⇒ BLOCKED (a lens silently dropping out is not a clean review). This is the R3 close specialized to personas.

**H14 — A6 "folded upstream / recorded" isn't verified to exist.**
`resolution.folded_upstream:[plan_ids]` and `deferred[]` are just strings in the manifest. A `fix_target=spec|code` item can be marked folded into a plan that doesn't exist — the doc fix is skipped and nothing catches it.
*Close:* Each id in `folded_upstream` must resolve to an existing plan file / issue artifact (`os.path.exists(plans/<id>.py)` or an open issue id in the shared queue); unresolved id ⇒ BLOCKED. Each `deferred[]` item must carry `{finding_id, reason, tracking_id}`; a deferral without a tracking id ⇒ BLOCKED. A `fix_target=doc` finding that is neither in `doc_fixes_applied` nor `deferred` ⇒ BLOCKED (no finding may silently evaporate — the set of `effective_severity>=MEDIUM` findings must equal applied ∪ folded ∪ deferred).

**H15 — Manifest "always emitted" ≠ manifest complete.** (the priority deliverable can be a vacuous shell)
The proposal guarantees emission (good, it's code) but nothing asserts the required fields are present and non-placeholder. A manifest with `contributors:[]`, `drift_checks:{}`, `truth_sources:[]`, `phase_timings` missing keys is still "emitted" and can carry `verdict:PASS`.
*Close:* A **manifest-schema gate (G12)** that runs in Phase 5 *before* the verdict is written and can itself force `BLOCKED`. It requires: all inherited spine keys present and typed; `phase_timings` has all six keys with `>0` for phases that ran; `gate_verdicts[]` contains exactly the expected `{G7..G12}` set (a missing gate entry ⇒ the gate didn't run ⇒ BLOCKED — closes R1 at the manifest layer too); `work.drift_checks` has all five sub-probes each with a `probe_status`; `selection.personas[]` non-empty with `ce_floor_satisfied` derived. The verdict function reads only validated fields.

**H16 — Thinking-level heuristic is a coverage-reduction lever.** (skip-by-downgrade)
`casual` (≤3 files) drops to maintainability-only, G7/G8-only, example-runnability on changed docs only. An adversary sizes the corpus to ≤3, or reviews a big doc set one file per invocation, to legally skip G9/G10/G11 and 4 of 6 lenses.
*Close:* Define a **non-negotiable floor that runs at every level**: H1 empty-corpus refuse, G7 (with H3 example-binding), G8, G9 path-liveness, G12 manifest-schema, and the CE floor (maintainability+adversarial). Thinking level may only *add* lenses/breadth (more personas, whole-repo example execution), never remove a floor gate. Encode the floor as a constant set the runner unions in regardless of level; record `thinking_level` AND `floor_gates_run[]` in the manifest and assert `floor ⊆ gates_run`.

**H17 — Run mutates the corpus ⇒ reproducibility claim breaks.**
A6 applies doc edits, so the `intake.corpus[].sha256` (pre-fix) no longer describes the state the PASS verdict pertains to. "Same docs, same verdict" is false across a fixing run.
*Close:* Record both `intake.corpus[].sha256_in` and `manifest.corpus_sha_out` (post-fix), and run the Phase-4 gates on the **post-fix** state. The reproducibility guarantee is: a re-run whose `sha_in == prior sha_out` and with `resolution.doc_fixes_applied==[]` must reproduce `verdict`. State this scope explicitly rather than implying byte-stable verdicts across a mutating run.

**H18 — No REFUSE path in the verdict primitive; `{plan}` placeholder undefined for doc-review.**
`workflow_verdict` returns only PASS/BLOCKED. The 3-step shipped `doc-review` also has no `{plan}` (A6 needs a model-chosen one).
*Close:* Extend `workflow_verdict(statuses) -> {PASS,BLOCKED,REFUSE}`: `REFUSE` iff a Phase-1 charter/truth-source gate is unresolved (terminal, emitted with manifest); `BLOCKED` iff any status is `blocked` (incl. mapped `could_not_run`, unexecuted judgment, schema failure); else `PASS`. For A6, the routed plan id is an output artifact validated by H14, not a workflow input placeholder.

---

# HARDENED `lathe doc-review` — implementer spec

**Identity:** a *drift invocation*. Verdict domain `{PASS, BLOCKED, REFUSE}`. **PASS only if** every floor gate ran (`ran_clean`/`ran_found→resolved`) and no `effective_severity=HIGH` finding is unresolved and manifest-schema is valid. **BLOCKED** on any drift/gate that ran-and-found or `could_not_run`. **REFUSE** iff the charter's truth-source or a machine-injected HIGH charter item was never `decided`.

## Ordered steps (typed; every guard is deterministic code)

**Phase 0 — Intake `[AUTO/code]`**
- A0 classify=`doc-review`; mint `run_id`; snapshot HEAD; resolve corpus (explicit `{files}` else default glob `*.md` root + `docs/*.md` minus `_archive/`); `sha256_in` + `size_bytes` per file; set `thinking_level`.
- **G0 (empty-corpus refuse):** `corpus_count>=1` and every `size_bytes>0`, else terminal REFUSE (`empty_corpus`). *[closes H1]*

**Phase 1 — Front-end `[skill+model, output gated]`**
- A1 `assumption-auditor` writes `<run>.charter.md`: truth-source ranking (per item `resolution∈{defaulted,decided}`), audience, severity bar. Machine step **auto-injects one HIGH charter item per** `dangling_path`/`doc_only_var`/denylist-hit found by a pre-pass of A4. *[closes H6]*
- **G1 (assumption-gate, fail-closed):** REFUSE if truth-source unresolved. Under STRICT: any HIGH item with `resolution=defaulted` ⇒ BLOCKED. Machine-injected HIGH items must be `decided`. *[H6, H8]*

**Phase 2 — Selection `[code mechanics + data catalog]`**
- A2 select doc lenses (grade-weighted, license-gated fetch): floor = `maintainability` + `adversarial` (CE); +`project-standards`,`docs-architect` at medium; +`reference-builder`/`api-documenter`,`tutorial-engineer` at high. Record `{name,source,license,match_score,rating,why_selected}`.
- **G2 (ce-floor derived):** `ce_floor_satisfied` computed from ran-contributors, not preset. *[H12]*

**Phase 3 — Work**
- A3 `[AUTO]` each selected persona reviews corpus vs charter truth-source, in parallel; each finding structured `{id,doc,line,model_severity,claim_in_doc,contradicting_truth,category,fix_target,status}`; each contributor records `status∈{ran,errored,skipped}` + `evidence.files_examined`. *[H13]*
- A4 `[AUTO] lathe doc-claims` — five deterministic probes, each returns `probe_status∈{ran_clean,ran_found,could_not_run}` and fails-closed (rc 2 = could_not_run ⇒ BLOCKED):
  1. docs_drift: `undocumented_cmds[]` (with example-binding, H3) + `stale_cmds[]` (H4)
  2. env_drift: `undocumented_vars[]` + `doc_only_vars[]` (H5); `unused` advisory
  3. path_liveness: `dangling_paths[]` + `placeholder_hits[]` (denylist); `checked_count>0` if any path token present (H10)
  4. example_runnability: `fenced_blocks_total`, `examples_extracted`, `run`, `failed[]`; require `run==examples_extracted` (H9)
  5. claim_checks: `count_claims_checked`, `mismatches[]` (H11)
- Y5 `[YOU/analyst, output gated]` triage → emits `triage.json` with a decision per finding; compute `effective_severity=max(model_severity, machine_floor)` where machine_floor=HIGH iff corroborated by a probe. *[H7]* Doc edits allowed here (docs are hand-maintained data — the one place edits don't violate "never hand-edit").
- A6 `[AUTO]` apply doc fixes; route `fix_target=spec|code` to bug-fix/enhancement. Record `doc_fixes_applied[]`, `folded_upstream[]`, `deferred[]`.
  - **G6 (resolution-coverage):** `{findings with effective_severity>=MEDIUM} == applied ∪ folded ∪ deferred`; every folded id resolves to a real plan/issue; every deferred item has `{reason,tracking_id}`. *[H14]*

**Phase 4 — Adversarial gate `[code enforces; all fail-closed; run on post-fix state]`** *[H2, H17]*
- G7 docs_drift (example-bound + reverse) · G8 env_drift · G9 path-liveness+placeholders · G10 example-runnability (with extract/run reconciliation) · G11 no unresolved `effective_severity=HIGH`.
- **Floor set that runs at every thinking level:** {G0, G7, G8, G9, G12, CE-floor}. Level may only add breadth. Record `floor_gates_run[]`; assert `floor ⊆ gates_run`. *[H16]*

**Phase 5 — Manifest `[AUTO/code — never optional]`**
- **G12 (manifest-schema, runs before verdict):** all spine keys present/typed; all six `phase_timings` keys `>0` for run phases; `gate_verdicts[]` == expected `{G7..G11}` (missing entry ⇒ BLOCKED, closes R1 at manifest layer); five drift sub-probes each carry `probe_status`; personas non-empty. *[H15, R1]*
- A12 `render_report` over validated fields; verdict via extended `workflow_verdict → {PASS,BLOCKED,REFUSE}`. Always written, even on REFUSE. *[H18]*

## Primitive changes required (not optional — the guarantees don't exist without them)
1. `classify_step`: `you` step with a required-but-missing artifact ⇒ `blocked`, not `todo`. `auto` step with empty output on a probe that should produce a count ⇒ `blocked` (proof-of-work, not string-sniff). *[R2, R3]*
2. `workflow_verdict`: codomain `{PASS,BLOCKED,REFUSE}`; `could_not_run`→BLOCKED; unresolved-charter→REFUSE. *[R1, R2, R18]*
3. Gates: replace `return 0` skip paths with `return 2` (could_not_run); runner treats rc 2 on a required probe as BLOCKED. *[R1, H2]*
4. `undocumented_commands`: require an invoking fenced example per command; add reverse (stale) check. *[H3, H4]*

## Exact manifest fields (`docs/ce/<run_id>.doc-review.manifest.json`)
Spine: `run_id, invocation:"doc-review", timestamp, git_commit, thinking_level, floor_gates_run[], models[], tokens:{in,out}, cost_usd, wall_ms, phase_timings:{intake,frontend,selection,work,gate,manifest}, verdict∈{PASS,BLOCKED,REFUSE}`.
- `intake.corpus[]:{path,sha256_in,size_bytes}`, `intake.corpus_count`, `intake.corpus_sha_out`, `intake.corpus_selection_reason`
- `frontend.truth_sources[]:{source,rank,resolution∈{defaulted,decided}}`, `frontend.audience`, `frontend.severity_bar`, `frontend.charter_assumptions[]:{claim,resolution,materiality,origin∈{model,machine_injected}}`, `frontend.unresolved_blocking[]`
- `selection.personas[]:{name,source,license,lens,match_score,rating,why_selected,status∈{ran,errored,skipped}}`, `selection.ce_floor_satisfied` (derived)
- `work.contributors[]:{name,status,evidence:{files_examined,bytes_examined},findings_count,findings:[{id,doc,line,model_severity,effective_severity,machine_floor:bool,claim_in_doc,contradicting_truth,category,fix_target,status}]}`
- `work.drift_checks`: `docs_drift:{probe_status,undocumented_cmds[],stale_cmds[]}`, `env_drift:{probe_status,undocumented_vars[],doc_only_vars[],unused_advisory[]}`, `path_liveness:{probe_status,checked_count,dangling_paths[],placeholder_hits[]}`, `example_runnability:{probe_status,fenced_blocks_total,examples_extracted,run,failed[]}`, `claim_checks:{probe_status,count_claims_checked,mismatches:[{claim,doc_value,truth_value}]}`
- `gate_verdicts[]:{name∈{G7..G12},pass:bool,probe_status,detail}`
- `resolution:{doc_fixes_applied[],folded_upstream:[{plan_id,exists:bool}],deferred:[{finding_id,reason,tracking_id}]}`
- `outcome:{verdict,blocking_reason?,refuse_reason?}`

**Code/skill split preserved:** spine, step order, the five drift probes, all gates, manifest-schema, and verdict math are deterministic code (non-bypassable). Persona bodies, charter authoring, and Y5 triage are skill+model whose *artifacts* are schema-gated. The hole in the proposal was never the architecture — it was trusting four primitives (`classify_step`, `workflow_verdict`, and the two gates' `SKIPPED==0`) that let the whole spine pass without doing the work.

Grounding files: `/home/user/lathe/projects/agentic-harness/tools/workflows.py`, `/home/user/lathe/projects/agentic-harness/tools/flow_report.py` (and its plan `plans/W01_flow_report.py`), `/home/user/lathe/projects/agentic-harness/qa/docs_drift_gate.py`, `/home/user/lathe/projects/agentic-harness/qa/env_drift_gate.py`, `/home/user/lathe/projects/agentic-harness/tools/undocumented_commands.py`, `/home/user/lathe/projects/agentic-harness/tools/env_logic.py`, `/home/user/lathe/env_catalog.py`, `/home/user/lathe/docs/DOC_CRITIQUE.md`, `/home/user/lathe/docs/OPERATING_CONTRACT_DESIGN.md`.