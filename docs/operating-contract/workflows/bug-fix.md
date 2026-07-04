I have enough grounding in the real mechanisms (`cmd_flow` at `lathe.py:896`, `flow_report` classify/verdict, `regression_proof.proof_gate`, the gate semantics in `GATES_REFERENCE.md`, and the current `workflows.py` bug-fix). Here is the adversarial critique and hardened spec.

---

# ADVERSARIAL CRITIQUE — `lathe bug-fix`

## The two structural flaws everything else hangs off

Before the per-step holes, two facts about the *actual* runner make most of the proposed guards vacuous as written:

**S1 — `todo` is a silent PASS.** In `cmd_flow` (`lathe.py:930-951`), every `you` step is printed and recorded as `classify_step("you",0,"")=='todo'`. `workflow_verdict` (in `W01_flow_report.py`) returns `BLOCKED` only if some status `=='blocked'`; `todo` and empty both map to `PASS`. **A bug-fix run whose triage, diagnose, fix, and release steps are all `you` returns PASS having produced nothing.** The proposal narrates gates on those steps ("refuse to advance unless…") but the runner has no mechanism to enforce them — they're print statements.

**S2 — no durable manifest exists, and the output signal is dead.** `render_report` prints a transient string; nothing is written to `docs/ce/`. Worse, `cmd_flow` calls `classify_step(kind, rc, "")` (line 944) — it passes `output=""` always, so the failure-signal detection (`traceback`, `error:`, `fail ::`) in `classify_step` is **dead code**. A step that prints a Traceback but returns `rc=0` classifies as `pass`. Verdict is rc-only, and the manifest — the stated priority deliverable — does not exist.

Every hardening below assumes these two are fixed first (see Hardened Workflow §A and §F).

---

## Hole-by-hole (attack → deterministic check that closes it)

### A. Triage brief (step 2) — placeholder passes

| ID | Attack | Deterministic check |
|---|---|---|
| **A1** | `<plan>.bugreport.md` is written with `repro_input`/`expected` present but placeholder (`""`, `TBD`, `...`, "see above"), or `repro_input` isn't a runnable assertion. File-exists ≠ work-done. | Brief must carry a machine-readable block (JSON front-matter): `repro_input`, `expected`, `violated_criterion`. Validator (code) rejects sentinel/empty values; `ast.parse`s `repro_input` and requires it be an `assert` statement **that names the target function**; and requires `violated_criterion ∈ CRITERIA` of `<plan>.py` (string-membership check). Fail any → REFUSE. The *real* enforcement is that step 3 executes this assertion — a non-runnable brief can't reproduce, so the run REFUSES by construction. |
| **A2** | `--thinking casual` short-circuits triage entirely, so the handed-in regression test is never validated. | The casual short-circuit may skip the *interview* only, never the *validation* or the RED observation. Separate `clarify_ran` (interview happened) from `brief_valid` (A1 passed) from `reproduced_red`. A casual run is `clarify_ran=false, brief_valid=true, reproduced_red=true`; the latter two are non-optional at every level. |

### B. Reproduce-RED (step 3) — false RED

| ID | Attack | Deterministic check |
|---|---|---|
| **B1** | The assertion "fails" with `NameError`/`ImportError`/`TypeError` (a broken test), not `AssertionError`. "Requires FAIL" is satisfied by any exception → phantom reproduced. | Sandbox must return the exception **type**. RED is valid **only** if `failure_mode=="assertion"`. `error` (any other exception) → REFUSE: "repro test is broken, not RED." Manifest `reproduction.failure_mode ∈ {assertion, error, pass}`; only `assertion` proceeds. |
| **B2** | No prior pin / target function absent from the module → assertion errors because the function is missing → looks RED, but there is no old code to regress against (colludes with C1). | Reproduce first asserts the target exists in the pinned module (`extract_def(old_src, fn) != ''`) and `before_pin_hash` is real (present in `.pins.json`). No prior implementation ⇒ this is not a bug-fix ⇒ REFUSE and route to `do`/`enhancement`. |
| **B3** | Sandbox imports the working-tree module (already half-edited), not the pinned bytes; or imports the single extracted def in isolation and NameErrors on module-level helpers → false RED. | Materialize the **full old module from `before_pin_hash`** (content-addressed) into an isolated sandbox and run the assertion there. Bind `reproduction.ran_against_pin == before_pin_hash`. Never run against the working tree. |

### C. Regression-proof (step 10, the centerpiece) — vacuous proof

| ID | Attack | Deterministic check |
|---|---|---|
| **C1** | **Rename bypass.** Rename `parse`→`parse_v2` in the plan; `extract_def(old_module,'parse_v2')=='' ` → `proof_gate` returns "no prior implementation - new function" → PASS with zero proof. (`rename_candidates` exists in `H_regression_proof.py` but the proposal never wires it.) | In bug-fix the new-function exemption is **forbidden** (B2 guarantees a prior impl). Before granting it, run `rename_candidates(old_src, current_names)`; a disappeared top-level def supplies `old_code` for the renamed unit. Assert `regression_proof.new_function_exemption_used==false`; if `before_pin_hash!=null` and `old_code==''`, REFUSE. |
| **C2** | Run step 10 as plain `lathe build` (not `LATHE_STRICT=1`). `proof_gate` with `env_value` unset returns `[False,'regression-proof not required']` → PASS, centerpiece no-ops. | Dispatcher (code) SETS `LATHE_STRICT=1 LATHE_REGRESSION_PROOF=1 LATHE_LINT_SPEC=block` itself; the skill cannot unset them. A bug-fix manifest whose `regression_proof.reason=='regression-proof not required'` or `gate_ran==false` ⇒ verdict REFUSED. |
| **C3** | The test confirmed RED at step 3 is silently weakened/dropped at step 7; step 10's proof rides on a *different* new test. The "one artifact, three checkpoints" story is broken. | Hash the exact RED assertion at step 3 → `red_test_hash`. Require that hash to be present verbatim in the plan's `tests` at step 10, and `old_pin_hash==before_pin_hash`. `regression_proof.red_test_hash` must equal `reproduction.red_test_hash`, else REFUSE ("shipped test is not the reproduced test"). |
| **C4** | `proof_gate` only checks `old_passes_all==False` — satisfied by ANY unrelated new test that happens to fail on old code, while the bug's own test is weak/absent. | Bind the proof to the RED test specifically: record a per-test old/new result vector keyed by test hash; require `red_test_failed_on_old==true AND red_test_passed_on_new==true` for that exact hash — not the aggregate. |

### D. Diagnose (5) / lint-spec (6) — inert judgment

| ID | Attack | Deterministic check |
|---|---|---|
| **D1** | Diagnose returns `fault_class:"impl", location:"<module>.py"` — technically "names a location," vacuously consistent. Free-text `you` step. | Structured output: `fault_class ∈ {spec,oracle,weak-test,impl}` + `location` that must resolve to a real symbol — a `CRITERIA` id (spec/oracle) or the target function (weak-test/impl), verified against `<plan>.py`. Tie to a downstream obligation: `weak-test` ⇒ step 7 must add a test kind or REFUSE; `oracle` ⇒ `assumption_policy` must be `med` and `thinking_level` bumped +1, and `diagnosis.escalated==true` recorded — if the escalation didn't apply, REFUSE. An inert diagnosis becomes incoherent by construction. |
| **D2** | lint-spec runs in default `warn`; or the surviving stub is on an *unrelated* function; or the plan is treated as ARTIFACTS so the probe is skipped. | Dispatcher forces `LATHE_LINT_SPEC=block`. Scope the survivor check to the **target function**: any trivial stub surviving the target's tests is a hard REFUSE. `diagnosis.lint_spec_survivors[]` keyed by function. |
| **D3** | "Diagnose from trace" assumes a build-fail log exists — but a behavioral bug builds GREEN and banks nothing in `_fn_fails/`. The step has no input → blocks or voids. | Authoritative evidence is the step-3 RED observation, which always exists. `trace_ref`/`banked_fail_ref` may be null; `red_observation_ref` is REQUIRED. Diagnose never voids for a green-building behavioral bug. |

### E. Sibling synthesis (11) / no-regression (12) — passes by producing weak cases

| ID | Attack | Deterministic check |
|---|---|---|
| **E1** | Model emits N siblings all far from the boundary (lengths 5,6,7 when the bug is at 0/1/max) → zero failures → "passes," point-fix undetected. The gate rewards *producing N cases that all pass*. | Siblings are **code-generated deterministic neighbors** of `repro_input` by type (numeric → ±1, 0, MAX; string → empty, len±1; collection → empty, singleton, dup) — not model-chosen, so a lazy model can't dodge the boundary. Model adds semantic siblings on top. Require: `repro_input` itself is in the set and PASSES on new code; **≥1 sibling was RED on the old pin** (proves the set is inside the blast radius, else vacuous). `deterministic_neighbors_covered==true`. |
| **E2** | Model returns fewer than N cases (2 when N=8) and the step still passes because those 2 pass. | Hard count gate in code: `len(sibling_cases) >= N` or REFUSE. N floor derived from **bug class** (security/data/reliability → high N) regardless of the thinking dial, cross-checked against the domain persona that fired at step 4. |
| **E3** | `lathe gate` (step 12) is tree-hygiene (stale/pristine/dups/docs/env) — it does NOT re-run behavior. The fix breaks another pinned function whose weak tests still pass → green gate, real regression missed. | Add a distinct `no_behavioral_regression` gate: after the new pin, re-run the pinned test-suite of the **dependency closure** (functions importing/imported-by the touched module). A green `lathe gate` alone does not satisfy no-regression; both are separate `gates[]` entries. |

### F. Review (13) — advisory, non-blocking

| ID | Attack | Deterministic check |
|---|---|---|
| **F1** | Decider picks 0 personas (empty market match) → "reviewed, 0 findings" vacuously; or real findings are recorded but never folded — review is advisory, nothing blocks. | Assert CE floor: `len(personas)>=2` with correctness + adversarial both present, else REFUSE (selection integrity). Each finding carries `adversarial_verified`, `real`, `folded_upstream`. A finding with `real==true && folded_upstream==false` ⇒ verdict BLOCKED. "Folded" is verified by re-hashing the plan: a fold changes the digest, forcing re-ack + re-build (fresh `new_pin_hash`). |

### G. Ack (8) / assume (9) — faked accountability

| ID | Attack | Deterministic check |
|---|---|---|
| **G1** | Autonomous mode auto-acks (fakes the human read); `assume --accept-all` bulk-clears blockers; or mis-diagnose as `impl` to keep policy at `high` so a `med` assumption slips. | (a) The autonomous ack is an analyst call whose OUTPUT is gated: require a recorded rationale that references `red_test_hash`; empty rationale ⇒ invalid ack. (b) `--accept-all` disabled under bug-fix; each blocker resolved individually, `blocking_assumptions_resolved[]` must list each with a non-placeholder resolution in `<plan>.decisions.md`. (c) Policy is set by the dispatcher from `fault_class` (oracle⇒med), not by the analyst (closes the mis-diagnose route via D1's escalation record). |

### H. Manifest — missing / incomplete / false PASS

| ID | Attack | Deterministic check |
|---|---|---|
| **H1** | Process dies before the final "emit manifest" step → no durable record at all. | Manifest is NOT a final step. Dispatcher opens `docs/ce/<run_id>.bug-fix.manifest.json` at **intake** with `verdict:"INCOMPLETE"`, all fields null, and **rewrites it after every phase** (atexit/`finally`-registered). A crash leaves `verdict:"INCOMPLETE"` + `phase_reached`. A missing manifest file for a live `run_id` is itself a CI-detectable failure. |
| **H2** | Manifest is emitted with empty centerpiece (`regression_proof:{}`) but stamped PASS. | A code `manifest_complete` schema gate runs before any non-INCOMPLETE verdict is stamped. PASS requires ALL: `before_pin_hash!=null`; `failure_mode=="assertion"`; `red_test_failed_on_old==true`; `red_test_passed_on_new==true`; `old_pin_hash!=new_pin_hash`; `reproduction.red_test_hash==regression_proof.red_test_hash`; `point_fix_detected==false` with `len(sibling_cases)>=N`; every load-bearing `gates[]` entry non-`skip`; no unresolved real review finding. Any miss ⇒ verdict downgraded to REFUSED/BLOCKED. **PASS is computed from evidence, never asserted by the skill.** |
| **H3** | (= S1) All judgment steps are `todo` ⇒ not-blocked ⇒ PASS. | In an executed (`--run`) bug-fix, `todo` is illegal: a judgment step must emit a gated artifact (brief JSON / diagnosis JSON / decisions file) whose code check yields `pass`/`blocked`. `todo` is legal only in dry view. Verdict = PASS iff every step is `pass` AND all H2 invariants hold. |

### I. Routing / spoofing

| ID | Attack | Deterministic check |
|---|---|---|
| **I1** | Fix the bug via bare `lathe build <plan>` — skips reproduce-RED, sibling synthesis, and manifest entirely. | Per the spine's non-bypass principle: `engine_v2` on a **pin-replacement of an existing pinned function** must (a) emit a manifest (every invocation does) and (b) run the adversarial phase. Absent a linked bug-fix `run_id` with a valid reproduce-RED + regression-proof record, and with `LATHE_REGRESSION_PROOF` on, it already refuses without a failing-on-old test — the sibling + manifest guarantees are attached to the pin-replace event, not the entry command. The bug-fix skill only adds the triage front-end on top. |
| **I2** | `--pin <hash>` spoofs `before_pin_hash` to a hash where the "bug" is trivially RED or where old==new (no-op). | `before_pin_hash` is READ from `.pins.json` for the named function, not accepted from CLI. If `--pin` is given it must MATCH; mismatch ⇒ REFUSE. `old_pin_hash!=new_pin_hash` enforced (H2). |

### J. Release (15)

| ID | Attack | Deterministic check |
|---|---|---|
| **J1** | `checkin --push` only checks red-gate/dirty-tree/behind-remote — a BLOCKED bug-fix (point-fix detected) still pushes if standing gates are green. | Release binds to the run's manifest: refuse unless `manifest.verdict=="PASS" && red_test_passed_on_new==true && point_fix_detected==false`. `released.checkin` records the manifest verdict it gated on. |

### K. Thinking-level & class starvation

| ID | Attack | Deterministic check |
|---|---|---|
| **K1** | Bug class is keyed off report keywords the reporter controls. A data-corruption bug worded as "wrong output" gets no `data-integrity-guardian`, no elevated N, no high thinking. | Re-evaluate selection AFTER diagnosis: force the domain floor when the fix location touches a configured sensitive-path map (auth/crypto/serialization/persistence) OR `violated_criterion` mentions integrity/security — independent of report wording. `selection.domain_floor_source ∈ {report-keyword, diagnosis-location, criteria}`. |
| **K2** | Strip severity words → `casual` → thin coverage (N=3, mutation 0.5) on a real security bug. | Thinking level may be auto-**raised** by evidence (fault class, touched files, sibling-RED count) but never auto-**lowered** below the floor implied by domain persona/criteria. `casual` requires input+expected present AND no sensitive file touched AND no domain persona floored; conflict ⇒ escalate. `thinking_source ∈ {auto, override, escalated}`. |

### L. Minor hardening
- `extract_def` uses `ast.get_source_segment`, which **excludes decorators** — an old function whose behavior depends on a decorator runs wrong in isolation. Mitigated by B3 (materialize the full module from the pin, not the single def). Record `regression_proof.old_code_source: "full-module-from-pin"`.

---

# HARDENED WORKFLOW — implementer spec

## §A Runner-level fixes (prerequisites — without these, all step guards are theater)

1. **Kill `todo`-as-pass.** In an executed bug-fix run, judgment steps emit a gated artifact; status derives from a code validator (`pass`/`blocked`), never bare `todo`.
2. **Feed real output to the classifier.** Replace `classify_step(kind, rc, "")` with the captured stdout/stderr so the dead failure-signal path (`traceback`/`error:`) becomes live; keep rc as the primary signal.
3. **Manifest opened at intake, rewritten per phase, closed in `finally`.** Default `verdict:"INCOMPLETE"`, `phase_reached` stamped continuously.
4. **Verdict computed by a `manifest_complete` schema gate (H2), not by `workflow_verdict`'s blocked-only logic.**
5. **Dispatcher owns the env** (`LATHE_STRICT=1 LATHE_REGRESSION_PROOF=1 LATHE_LINT_SPEC=block`, policy from fault class); the skill cannot unset it.

## §B Ordered steps with inline guards

| # | Phase | Type | Action | Guard (code) → verdict on fail |
|---|---|---|---|---|
| 1 | Intake | A | classify=`bug-fix`, mint `run_id`, **read** `before_pin_hash` from `.pins.json` for the named fn (I2), seed thinking. Open manifest `INCOMPLETE`. | fn not pinned / not in module ⇒ REFUSE (B2). `--pin` mismatch ⇒ REFUSE (I2). |
| 2 | Front-end | Y→gated | Triage brief JSON: `repro_input` (assert naming the fn), `expected`, `violated_criterion`. | A1 validator: sentinel/empty, non-`assert`, non-member criterion ⇒ REFUSE. Casual skips interview only (A2). |
| 3 | Front-end | G | Reproduce-RED: run `repro_input` against full old module from `before_pin_hash` in sandbox. Record `red_test_hash`, `failure_mode`. | `failure_mode!="assertion"` (pass or error) ⇒ REFUSE (B1/B3). |
| 4 | Selection | A | Decider + CE floor + domain floor by class. | `len(personas)<2` or floor personas absent ⇒ REFUSE (F1). |
| 5 | Selection | Y→gated | Structured diagnosis `{fault_class, location, escalation}`; **re-evaluate domain floor from location** (K1). | Location unresolved / obligation-incoherent ⇒ REFUSE (D1). `oracle` ⇒ set policy=med, thinking+1, `escalated=true` (D1/G1c). |
| 6 | Selection | A+G | `lint-spec` (block) scoped to target fn. | Target-fn stub survivor ⇒ REFUSE (D2). |
| 7 | Work | Y | Fold `red_test_hash` test into `tests`; fix spec/CRITERIA; declare `kinds` per fault class. Never hand-edit code. | `weak-test` diagnosis with no kind added ⇒ REFUSE (D1). |
| 8 | Work | A | `ack` with rationale referencing `red_test_hash`. | Empty rationale ⇒ invalid ack (G1a). |
| 9 | Work | A+G | `assume` (policy from step 5); resolve blockers individually. | `--accept-all` disabled; unresolved ≥policy blocker ⇒ BLOCKED (G1b). |
| 10 | Work | A+G | `LATHE_STRICT=1 build`. Regression-proof keyed to `red_test_hash`. | `new_function_exemption_used` / `reason=="not required"` (C1/C2); `red_test_hash∉tests` or `old_pin==new_pin` (C3); `red_test` not failed-on-old / not passed-on-new (C4) ⇒ REFUSE. |
| 11 | Adversarial | A+G | Sibling synthesis: **deterministic neighbors** of `repro_input` + model semantic siblings, run on new pin. | `len<N` (E2); no neighbor RED-on-old (E1); any sibling fails on new ⇒ `point_fix_detected=true` ⇒ BLOCKED. |
| 12 | Adversarial | G | `lathe gate` (hygiene) **and** `no_behavioral_regression` over dependency closure. | Either red ⇒ BLOCKED (E3). |
| 13 | Adversarial | A | `review auto`; adversarial-verify findings. | `real && !folded_upstream` ⇒ BLOCKED (F1). A fold re-triggers 7→10. |
| 14 | Manifest | A | `manifest_complete` schema gate computes verdict from evidence; write final. | Any H2 invariant unmet ⇒ verdict REFUSED/BLOCKED (H2). |
| 15 | Release | Y+G | `checkin --push` bound to manifest verdict. | `verdict!=PASS` or `point_fix_detected` ⇒ refuse release (J1). |

## §C Exact manifest — new/changed fields vs the proposal

Keep the proposed schema; add these deterministic invariants (the load-bearing additions):

```jsonc
"verdict": "PASS | BLOCKED | REFUSED | INCOMPLETE",   // INCOMPLETE default at intake (H1)
"phase_reached": 0..5,                                 // last phase written (H1)

"intake": { ..., "before_pin_hash",                    // READ from .pins.json, never from --pin (I2)
            "pin_arg_matched": true|null },             // if --pin passed, must match

"front_end": { "clarify_ran", "brief_valid",           // split: interview vs validation (A2)
               "brief_criterion_in_plan": true, ... },

"reproduction": { "reproduced_red", "failure_mode": "assertion|error|pass",  // only assertion is RED (B1)
                  "red_test_hash", "ran_against_pin",   // == before_pin_hash (B3)
                  "old_code_source": "full-module-from-pin" },               // (L)

"diagnosis": { "fault_class", "location", "location_resolves": true,         // (D1)
               "escalated": true|false,                // oracle ⇒ true (D1/G1c)
               "red_observation_ref", "lint_spec_survivors": {fn: []} },     // (D2/D3)

"regression_proof": {                                   // centerpiece — per-test, keyed
    "gate_ran": true, "reason",                         // reason!='regression-proof not required' (C2)
    "new_function_exemption_used": false,               // forbidden in bug-fix (C1)
    "red_test_hash",                                    // == reproduction.red_test_hash (C3)
    "red_test_failed_on_old": true, "red_test_passed_on_new": true,  // that hash specifically (C4)
    "old_pin_hash", "new_pin_hash" },                   // must differ (C3/H2)

"selection": { "ce_floor_present": true,                // correctness+adversarial (F1)
               "domain_floor_source": "report-keyword|diagnosis-location|criteria", // (K1)
               "personas": [...] },

"adversarial": { "sibling_n_required": N,               // floored by class, not just thinking (E2)
                 "deterministic_neighbors_covered": true,        // (E1)
                 "sibling_cases": [{input, class, was_red_on_old, passes_on_new}],
                 "any_neighbor_red_on_old": true,       // blast-radius proof (E1)
                 "point_fix_detected": false },

"gates": [ ... "regression_proof", "spec_lint(target)", "no_behavioral_regression", ... ],
                                                        // distinct from hygiene `lathe gate` (E3)

"review": { "findings": [{persona, claim, adversarial_verified, real, folded_upstream}],
            "unresolved_real": false },                 // any true ⇒ BLOCKED (F1)

"thinking": { "level", "source": "auto|override|escalated", "floor_from": "..." },  // (K2)

"released": { "checkin", "gated_on_verdict": "PASS" }   // (J1)
```

## §D The one machine-checkable PASS predicate (the `manifest_complete` gate)

```
PASS  ⟺
  before_pin_hash ≠ null
  ∧ reproduction.failure_mode == "assertion"
  ∧ reproduction.red_test_hash == regression_proof.red_test_hash
  ∧ regression_proof.gate_ran ∧ ¬new_function_exemption_used
  ∧ red_test_failed_on_old ∧ red_test_passed_on_new
  ∧ old_pin_hash ≠ new_pin_hash
  ∧ len(sibling_cases) ≥ sibling_n_required ∧ deterministic_neighbors_covered
      ∧ any_neighbor_red_on_old ∧ ¬point_fix_detected
  ∧ ce_floor_present ∧ ¬review.unresolved_real
  ∧ every load-bearing gates[] entry ≠ "skip"
otherwise REFUSED (proof/repro failures) or BLOCKED (adversarial/review/assume failures);
INCOMPLETE if the process died (default).
```

The verdict is a pure function of recorded evidence. The skill fills content; this predicate — code — decides. That is the difference between the proposal's narrated guards and an enforced contract.

## §E Implementation delta beyond the proposal's four items
The proposal names four gaps (reproduce-RED gate, triage front-end, sibling synthesis, manifest emission). This critique adds five that the four don't cover: **(5)** kill `todo`-as-pass and feed real output to `classify_step` (§A1–2 — without it the other four are unenforced print statements); **(6)** key regression-proof to `red_test_hash` per-test, not `old_passes_all` aggregate, and forbid the rename/new-function exemption in bug-fix (C1/C3/C4 — the centerpiece is currently satisfiable by an unrelated failing test or a rename); **(7)** deterministic code-generated sibling neighbors with a blast-radius proof (E1 — model-chosen siblings are gameable); **(8)** a `no_behavioral_regression` gate distinct from hygiene `lathe gate` (E3); **(9)** the `manifest_complete` predicate (§D) as the verdict authority, and manifest-opened-at-intake so a crash still leaves an `INCOMPLETE` record (H1/H2).