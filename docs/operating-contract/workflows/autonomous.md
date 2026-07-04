# Adversarial critique — INVOCATION: autonomous, and the hardened spec

The design's spine is sound (deterministic conductor, gated skill output, always-on manifest). But almost every *guarantee* is stated as intent, not as a mechanical check. Below, every place the loop can skip, produce nothing, emit an incomplete manifest, or pass vacuously — each with the exact deterministic check that closes it. Then the hardened workflow.

---

## A. How vacuity enters this design

Three vectors, present at every step:
1. **The step runs but its OUTPUT is empty/trivial** (analyst emits 0 criteria / decompose emits 0 tasks / adversarial emits 0 cases). The step "succeeded"; it did nothing.
2. **A gate passes over nothing** (regression green on an empty tree; adversarial green because no case was generated). Green ≠ evidence.
3. **A model self-labels to dodge a park** (materiality downgraded HIGH→MED; "no assumptions found"). The fail-closed rule is stated but nothing mechanically enforces it.

The fix pattern throughout: **every gate must record the evidence count it checked, and a PASS with zero evidence is defined as VACUOUS, not PASS.** No verdict is a model's word; each is recomputed from recorded counts at finalize.

---

## B. Hole-by-hole, with the deterministic check that closes each

### Phase 0 — Intake

**H1 — Empty/whitespace objective.** Arg absent and `_self_feed_objective.txt` empty/missing → whole run proceeds vacuously and reports `built:0` as success.
- **Check:** after strip, `len(objective) > 0` and passes a min-token floor; else halt at intake, finalize rollup with `verdict:REFUSE, reason:"empty-objective"`. Record `objective_source ∈ {arg,self_feed}` (arg wins; precedence fixed, not undefined).

**H2 — run_id collision / manifest overwrite.** Timestamp-derived id + two runs same second → silent overwrite of a prior run's record.
- **Check:** assert no existing `docs/ce/<run_id>.manifest.json`; if present and `--resume` not passed → REFUSE `run-id-collision`. run_id must be unique (uuid or monotonic counter, not bare second).

**H3 — "Partial record on crash" is indistinguishable from a complete one.** A crash-partial manifest looks like a finished manifest with some nulls.
- **Check:** manifest carries `schema_version` and `manifest_complete:false` written at open, flipped `true` only after finalize schema-validation passes. **Any manifest with `manifest_complete:false` is treated by the evaluator as `outcome:crashed`, never PASS.** Add `last_phase_completed:int`, bumped as each phase returns. Manifest writes are atomic (temp file + `os.rename`) so a crash mid-write never leaves corrupt JSON.

**H4 — Invalid thinking level.** Junk value silently coerced or crashes.
- **Check:** validate against `{casual,medium,high}`; else default `medium`; record both `thinking_raw` and `thinking_resolved`.

### Phase 1 — clarify → `OBJECTIVE.contract.md` (the biggest hole)

The step is AUTO (guaranteed to *run*), but its content is an analyst call and **nothing gates the contract's quality.** The entire run traces back to a document that can be an echo of the objective with zero testable content.

**H5 — Zero criteria / prose-only / non-testable contract.** Analyst emits a contract with no acceptance criteria, or criteria that are unverifiable prose. Everything downstream then has nothing to test against, and each per-task gate passes vacuously.
- **Check (structured, not NL-scraped):** contract MUST emit a machine-parseable block (JSON/front-matter). Enforce: `criteria_count ≥ 1`; every criterion has a unique non-empty `criterion_id`, a non-empty `success_signal`, and a `verification_kind ∈ {test,gate,check}`; `non_goals` present as an explicit array (may be `[]`, never missing). Fail any → the clarify GATE fails → run REFUSE `contract-nontestable`. **This step is upgraded from AUTO to AUTO+GATE.**

**H6 — Echo attack.** Criterion text == objective text (contract restates the ask without decomposing "done").
- **Check:** reject if any `criterion.text` is byte-equal to or ≥0.9 token-overlap with the raw objective; reject if all criteria collapse to one. Require ≥1 explicit `success_signal` that is not just the objective sentence.

### Phase 2 — assume → GATE

**H7 — Empty ledger = vacuous pass.** Auditor "finds no assumptions" and passes. Indistinguishable from the auditor not running or being lazy — the one defense against the loop baking in silent choices is toothless.
- **Check:** the ledger must contain **one explicit scan record per `criterion_id`.** "No assumptions for criterion X" must be a recorded, deliberate entry — silence for a criterion → gate FAIL `assumption-coverage-gap`. Emptiness is now a claim, not a skip.

**H8 — Materiality downgrade to dodge parking (completion-bias).** Model labels a genuinely HIGH item as MED so it auto-resolves instead of parking. The "unknown→HIGH" rule is stated but the model never says "unknown."
- **Check (mechanical, does not trust the label):** auto-resolution of ANY assumption is permitted **only if** it carries a concrete non-empty `safe_default` string AND a `default_source ∈ {config,contract,spec}` that resolves. **No resolvable default ⇒ park, regardless of the model's materiality label.** This closes the downgrade because dodging the park requires producing a real, sourced default — which is exactly the safe behavior you wanted.

**H9 — decisions.md never written / count mismatch.** MED/LOW claimed "auto-resolved" but no durable record.
- **Check:** `count(decisions.md entries) == count(auto_resolved assumptions)`; each entry `{assumption_id, default, source}`; mismatch → gate FAIL.

**H10 — Phase-ordering inconsistency.** Phase 2 writes `<plan>.decisions.md` but plans don't exist until Phase 3. Assumptions are per-criterion here, per-plan there.
- **Fix:** assumptions bind to `criterion_id` at Phase 2. At Phase 3 each task **inherits** the resolved/parked status of every criterion it covers; `.decisions.md` is materialized per task after decompose. A task covering ANY parked criterion is itself parked (see H16).

### Phase 3 — decompose → AUTO

**H11 — Empty decomposition.** Analyst emits 0 plans → build loop walks an empty DAG → `built:0` reported as success.
- **Check:** `tasks_total ≥ 1` else REFUSE `empty-decomposition`.

**H12 — Criteria not covered (the trivial-task dodge).** Decompose into one easy task, ignore the hard criteria. Run goes green having tested nothing that matters.
- **Check (the key anti-vacuous invariant):** `⋃ task.contract_criteria ⊇ {non-parked criterion_ids}`. Any non-parked criterion with zero covering task → REFUSE `criteria-uncovered` (or explicitly park the criterion with reason, surfaced). Coverage is recomputed at finalize, not trusted.

**H13 — "small, pure, ≥4 asserts" claimed but unchecked.**
- **Check:** count assertions in each plan's test block, reject `<4`; AST purity check on the gated region (no I/O/network/clock imports), reject impure; enforce a size ceiling. These are deterministic and belong in the decompose gate, not honor-system prose.

**H14 — DAG cycles / dangling edges.** `DEPENDS_ON` cycle → topological walk never terminates or silently skips; edge to a non-existent task_id.
- **Check:** cycle detection (REFUSE `cyclic-dag`); every edge endpoint must be an existing task_id (REFUSE `dangling-dep`).

**H15 — Persona selected-but-absent (silent lens loss).** `select_agents_for_goal` names a persona; license-gated fetch fails (network); spec is then authored *without* the lens but the manifest says the persona "fired." Vacuous expertise.
- **Check:** every entry in `personas_selected[]` must carry a resolved `body_hash` (the loaded persona text), not just a name. Unresolved body → task parked `persona-unavailable`, recorded — never silently authored without the lens. **CE floor:** assert `correctness-reviewer` present with resolved body on *every* plan; else inject-or-fail.

### Phase 4 — build loop → AUTO

**H16 — STRICT not actually on.** A task "builds" with `LATHE_STRICT` unset → mutation-score/regression-proof/etc. never composed → green is vacuous.
- **Check:** the loop asserts `LATHE_STRICT=1` at entry; record `strict:true` per task; a task with `status:built, strict:false` → gate FAIL `strict-off`.

**H17 — Fabricated / inconsistent counters.** `repairs_used>0` but `banked_failures[]` empty (repair without a real banked error), or `status:built` with `tries_used:0` (impossible).
- **Check:** `status:built ⇒ tries_used ≥ 1`. `repairs_used > 0 ⇒ len(banked_failures) ≥ repairs_used`, and **each banked ref must resolve to a file on disk in `_fn_fails/`** whose hash matches. Inconsistency → task manifest INVALID → not pinnable.

**H18 — Implementer escalation leak.** Nothing mechanically stops a repair path from calling the frontier model as implementer (violating binding-cost).
- **Check:** the implementer call site is pinned to the local model tier by config; `model_implementer` recorded per task; assert `model_implementer ∈ {allowed_local_tiers}` at pin time; frontier id in that field → gate FAIL `implementer-escalation`.

### Phase 5 — park-not-grind → GATE

**H19 — Fail-counter doesn't survive restart → infinite grind.** "≥3 cross-cycle" needs a counter; if in-memory, a crash/restart resets it.
- **Check:** fail-count persisted on the board keyed by `task_id`, incremented atomically; park decision reads persisted count. Cross-cycle means cross-process.

**H20 — Incomplete dependent-parking.** Only direct dependents parked → a grandchild builds on a missing base.
- **Check:** compute the **transitive closure** of the parked set over `DEPENDS_ON`; every task with a parked ancestor → `status:blocked-by-dep`. Closure completeness asserted (no task with an unbuilt/parked ancestor may enter the build loop).

**H21 — Parked task silently vanishes.** A parked task with no dependents just disappears from the record.
- **Check:** every task_id in the DAG must emit its own per-task manifest with `status` and `reason`, including `parked`/`blocked-by-dep`. Enforced at finalize by H27.

### Phase 6 — adversarial (per-task) → AUTO

**H22 — Zero adversarial cases = trivial green (classic vacuous gate).** Synthesize 0 cases → nothing to fold → "adversarial passed" → pin.
- **Check:** `adversarial.cases_generated ≥ min_cases(thinking)` (e.g. medium ≥3); zero → gate FAIL, cannot pin.

**H23 — Cases generated but not executed / survivors not folded but still pinned.**
- **Check:** `adversarial.executed == cases_generated`; **pin permitted only when `adversarial.survivors_after_fold == 0`** (green after folding). Unfolded survivors → task returns to repair or parks; it must not pin.

**H24 — Trivial adversarial cases (`assert True`, or copies of spec tests).** Cases exist but exercise nothing.
- **Check:** dedup each adversarial case by hash against existing spec tests (reject duplicates); require each case to reference/exercise the gated symbol (coverage delta > 0 over the function) or kill ≥1 mutant not already killed. A case that adds no coverage and kills no new mutant is dropped and not counted toward `min_cases`.

### Phase 7 — cross-task regression → GATE

**H25 — Green over an empty/zero-test tree.** `built:0` → regression trivially passes → owner gate sees green+pristine+auto_commit+zero-needs-owner → run reports PASS having produced and committed nothing.
- **Check:** record `regression.tests_collected`. If `tests_collected == 0` the verdict is **`VACUOUS`, not PASS.** Rollup `verdict` may not be PASS when `tasks_built == 0` (see D). Regression PASS requires `tasks_built ≥ 1 ∧ tests_collected ≥ 1`.

**H26 — Regression skipped by a crash before Phase 7.** Field never set → downstream can't tell it didn't run.
- **Check:** `cross_task_regression` defaults to `NOT_RUN`; the owner gate treats `NOT_RUN` and `VACUOUS` as **FAIL** (fail-closed). Only explicit `PASS` permits commit.

### Phase 8 — owner gate → GATE

**H27 — "Tree pristine" is ambiguous (pins are generated files).** A literal `git status --clean` fails because the build wrote pins; a loose check lets stray/hand-edited files ride along in the commit.
- **Check:** compute the **expected changeset** = exactly the pinned `plans/auto_*.py` (+ manifests + decisions) for built tasks. Assert `working_tree_diff ⊆ expected_set`; any file outside → NOT pristine → refuse `unexpected-diff`. Prevents both false-negatives (pins) and smuggled hand-edits.

**H28 — Branch-park failure loses work / leaves dirty tree** (violates the core "never an uncommitted dirty tree" guarantee). Branch already exists, detached HEAD, dirty index.
- **Check:** branch-park is atomic and *verified*: create `lathe/auto/<run_id>`, commit, then assert `commit_sha` resolves AND tree is now clean. If any step fails → record a recoverable `stash_ref` in the manifest and set `outcome:"refused-dirty"` explicitly. Never write `outcome:branch-parked` without a resolving `commit_sha`.

**H29 — Partial success silently touching mainline.** Some built, some parked — do the built ones go to mainline?
- **Rule made explicit + checked:** `zero needs-owner` is required for mainline; therefore ANY park/block → outcome is branch-park, never mainline. Assert: `outcome == committed ⇒ parked==0 ∧ blocked==0 ∧ needs_owner==0`.

### Phase 9 — attended YOU

**H30 — Step silently absent in autonomous mode** (can't tell "skipped-by-design" from "forgotten").
- **Check:** record `owner_gate.attended:false, reason:"autonomous"`. The step is a recorded no-op, not a gap.

### Phase 10 — manifest → AUTO (never optional)

**H31 — Emitted-but-incomplete.** The manifest exists but per-task manifests are missing for parked/blocked/crashed tasks, or required rollup fields are null.
- **Check:** at finalize, `count(per_task_manifests) == tasks_total` (every DAG task_id → exactly one manifest file); full **schema validation** — every required field present and typed. Any failure → `manifest_complete` stays `false` → outcome not PASS.

**H32 — Free tokens/cost (unreported usage).** Analyst wrapper returns no usage → tokens/cost default 0 → run looks free; a `built` task with `model_analyst` set but `analyst_tokens==0` is impossible.
- **Check:** every analyst call must return usage; `status:built ∧ model_analyst set ⇒ analyst_tokens > 0`. `cost_usd` computed deterministically from tokens × a pinned price table; null cost → INCOMPLETE.

**H33 — Vacuous "why".** `personas_selected[].why` is empty string.
- **Check:** `why` constrained to enum `{ce-floor, mandatory, "match-score:<float>", "fetched:<reason>"}`; empty/free → invalid.

**H34 — Pins don't recompute (repro claim is unverified).** "byte-reproducible via `lathe verify`" is asserted, never checked.
- **Check:** at finalize, recompute `sha256(spec+tests+model)` for each built task and assert it equals the recorded `spec_pin`; assert each pin resolves to an on-disk spec. Mismatch → flag `pin-drift`, verdict downgraded.

### Cross-cutting

**H35 — Spine bypass (skill calls `engine_v2` directly).** The whole guarantee rests on bare commands routing THROUGH the contract; a skill that pins/commits directly skips phases 1–2 and 6–8.
- **Check:** the flow-runner issues a `run_context` token at Phase 0. **`engine_v2` pin and any commit operation refuse to execute without a valid token.** The spine becomes non-bypassable in code, not by convention. A skill physically cannot pin or commit outside the contract.

**H36 — Top-line `verdict` is model discretion.** If any model or ad-hoc logic sets PASS/PARTIAL/REFUSE, it can lie.
- **Fix:** verdict is a pure function of recorded counts, computed once at finalize (see D).

**H37 — Traceability chain break.** objective → criterion_id → task → spec_pin → gate → manifest; a break anywhere = silently incomplete.
- **Check:** at finalize assert full linkage: every built task's `contract_criteria ⊆ contract.criterion_ids`; every `criterion_id` resolves; every gate verdict references an evidence count; every pin resolves. Any dangling link → `manifest_complete:false`.

---

## C. Non-bypass enforcement (the mechanism, not the promise)

- **Single entrypoint:** the flow-runner is the only code path that mints a `run_context` token. `engine_v2.pin()` and the commit/branch step assert a live token or refuse (`H35`).
- **Fail-closed defaults:** every gate field defaults to its FAILING value (`regression:NOT_RUN`, `manifest_complete:false`, `strict:false`). Nothing is PASS until explicitly set PASS with evidence.
- **Evidence-bearing gates:** no gate returns a bare boolean; each returns `{verdict, evidence_counts}` and a PASS with zero evidence is defined `VACUOUS` and treated as FAIL by the owner gate.
- **Crash handler:** `atexit`/signal hook best-effort finalizes with `outcome:crashed`, `last_phase_completed:n`, verdict recomputed from current counts — the manifest is durable even on abort (`H3`, `H31`).

---

## D. Mechanical verdict (removes all model discretion — `H25`, `H36`)

Computed once at finalize from recorded counts:

```
REFUSE  if tasks_built == 0
        or contract invalid (H5/H6)
        or empty decomposition (H11)
        or any criterion uncovered & not parked (H12)
        or cross_task_regression ∈ {FAIL, VACUOUS, NOT_RUN}
        or manifest_complete == false
PASS    if tasks_built == tasks_total
        and parked == 0 and blocked == 0 and needs_owner == 0
        and all non-parked criteria covered
        and cross_task_regression == PASS (tests_collected ≥ 1)
        and owner_gate.verdict == committed  (or branch-park per policy w/ resolving commit_sha)
PARTIAL otherwise  (some built, some parked/blocked; all manifests present;
                    regression PASS on built subset; landed on branch)
```

---

## E. Hardened step table

| # | Phase | Type | Action + closed guards |
|---|-------|------|------------------------|
| 0 | Intake | AUTO | run_id **unique** (H2); objective non-empty, source fixed arg>self_feed (H1); thinking validated (H4); open manifest `manifest_complete:false`, `schema_version`, `last_phase_completed:0` (H3); mint `run_context` token (H35). |
| 1 | clarify | **AUTO+GATE** | Analyst writes `OBJECTIVE.contract.md` as structured block. GATE: ≥1 criterion, each with `criterion_id`+`success_signal`+`verification_kind`, explicit `non_goals`, no echo (H5,H6). Fail → REFUSE. |
| 2 | assume | GATE | Ledger has one scan record **per criterion_id** (H7); auto-resolve only with resolvable `safe_default`+`default_source`, else park (H8); `decisions.md` count-matched (H9); assumptions bind to criterion_id (H10). |
| 3 | decompose | AUTO+GATE | `tasks_total≥1` (H11); criteria coverage ⊇ non-parked (H12); ≥4 asserts + AST-purity + size ceiling per plan (H13); DAG acyclic, no dangling edges (H14); each persona has resolved `body_hash`, CE floor present, unresolved → park `persona-unavailable` (H15). |
| 4 | build loop | AUTO | `LATHE_STRICT=1` asserted+recorded (H16); counter/bank consistency (H17); `model_implementer` in local tier (H18); bank→`repair_spec`→retry ≤ max_repairs. |
| 5 | park-not-grind | GATE | fail-count **persisted on board** (H19); transitive-closure dependent parking (H20); every parked/blocked task emits a manifest (H21). |
| 6 | adversarial (task) | AUTO+GATE | `cases_generated ≥ min(thinking)` else FAIL (H22); executed==generated, pin only if `survivors_after_fold==0` (H23); cases deduped + coverage/mutant-delta enforced (H24). |
| 7 | regression (tree) | GATE | record `tests_collected`; PASS requires `tasks_built≥1 ∧ tests_collected≥1` else `VACUOUS` (H25); default `NOT_RUN` = FAIL (H26). |
| 8 | owner gate | GATE | commit iff auto_commit ∧ regression PASS ∧ **diff ⊆ expected_set** (H27) ∧ needs_owner==0; branch-park atomic + verified `commit_sha` else `refused-dirty` (H28); partial never touches mainline (H29). |
| 9 | owner gate (attended) | YOU→GATE | autonomous: recorded no-op `attended:false, reason:autonomous` (H30). |
| 10 | manifest | AUTO | `count(per_task)==tasks_total` (H31); full schema validation; usage/cost non-null & consistent (H32); persona `why` enum (H33); pins recompute (H34); traceability linkage asserted (H37); flip `manifest_complete:true` only on all-pass; atomic write. |

---

## F. Hardened manifest fields

**Per-task** `docs/ce/<run_id>/task-<plan>.manifest.json` — emitted for **every** DAG task (built, parked, blocked, crashed):
```
schema_version, run_id, task_id, plan_path
depends_on[]
contract_criteria[]              // criterion_ids, must ⊆ contract ids (H12,H37)
personas_selected[]              // {name, source, license, body_hash(non-null), why(enum, non-empty)}   (H15,H33)
assumptions[]                    // {id, materiality, resolution: default|parked,
                                 //  safe_default, default_source, decisions_md_ref}                     (H8,H9)
strict                           // must be true for status:built                                       (H16)
spec_pin                         // sha256(spec+tests+model); must recompute at finalize                (H34)
model_analyst, model_implementer // implementer ∈ local tier                                            (H18)
build.tries_used                 // ≥1 if built                                                         (H17)
build.repairs_used
build.banked_failures[]          // len ≥ repairs_used; each ref resolves on disk                       (H17)
adversarial.cases_generated      // ≥ min_cases(thinking)                                               (H22)
adversarial.executed             // == cases_generated                                                  (H23)
adversarial.survivors_after_fold // must == 0 to pin                                                    (H23)
gates[]                          // [{name, verdict:PASS|FAIL|VACUOUS|NOT_RUN, evidence_counts:{...}}]   (evidence-bearing)
thinking_level
tokens:{analyst_in,analyst_out}, cost_usd   // non-null; >0 if built                                    (H32)
timing_ms
status                           // built | escalated | parked-needs-owner | blocked-by-dep | crashed
reason                           // required for any non-built status                                   (H21)
```

**Rollup** `docs/ce/<run_id>.manifest.json` (the evaluation instrument):
```
schema_version
manifest_complete: bool          // false at open, true only after finalize validation                 (H3,H31)
last_phase_completed: int        // crash forensics                                                     (H3)
run_id, invocation:"autonomous", entrypoint: auto|run|decompose
objective_text, objective_source: arg|self_feed, objective_contract_ref
contract: {criteria_total, criteria_ids[], nontestable_rejected: bool}                                  (H5)
thinking_raw, thinking_resolved                                                                         (H4)
decomposition: {tasks_total(≥1), dag_edges, acyclic:true, criteria_covered:bool}                        (H11,H12,H14)
tasks: {built, escalated, parked_needs_owner, blocked_by_dep, crashed}
per_task_manifests[]             // len == tasks_total                                                   (H31)
cross_task_regression: {verdict: PASS|FAIL|VACUOUS|NOT_RUN, tests_collected}                             (H25,H26)
owner_gate: {auto_commit_enabled, expected_diff_ok:bool, tree_pristine:bool,
             needs_owner_count, attended:false, reason, verdict, reason_detail}                          (H27,H29,H30)
outcome: committed | branch-parked-for-ratification | refused | refused-dirty | crashed                 (H28)
commit_sha | branch_ref | stash_ref     // commit_sha/branch_ref must resolve                            (H28)
totals: {analyst_calls, tokens, cost_usd, wall_time_ms}                                                 (H32)
personas_used[]                  // union, each with enum why                                            (H33)
traceability_ok: bool            // full objective→criterion→task→pin→gate linkage                       (H37)
repro_ok: bool                   // all pins recompute                                                   (H34)
verdict: PASS | PARTIAL | REFUSE  // pure function of counts above, computed at finalize                 (H36, §D)
```

**Finalize invariant (non-bypassable code):** `manifest_complete` flips to `true` only if — every DAG task has a manifest, schema validates, `traceability_ok`, `repro_ok`, all gate verdicts are evidence-bearing, and `verdict` recomputes consistently. Otherwise it stays `false` and the evaluator reads the run as crashed/refused. The rollup is written atomically at intake and at finalize, and by the crash handler on abort — so a durable, correctly-flagged record exists on every possible exit.