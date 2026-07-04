I've grounded the critique in the actual surface. Key facts that arm it: `cmd_review` (lathe.py:257) wraps every enrichment in bare `try/except → []`; `select_agents_for_goal` (agent_router.py) is pure bag-of-words `score>0` with **no grade** anywhere; `ratings.json` load/save exists but the review path never calls `save_rating`; there is **no `usage.jsonl`**; pins are `content-hash → source-string`, **not** `file → plan`; `hreview.py` emits **free text**, truncated `txt[-4000:]`, never parsed; and `run_gates.py` **silently `continue`s past any missing gate file** — so regression-proof/mutation/gate-the-glue (which don't exist there) are skipped and it still prints "regression clean", exit 0.

Here is the adversarial critique and the hardened spec.

---

# `code-review` contract — adversarial hardening

## A. Grounding: what the real code lets you get away with

| Real surface | Consequence for the proposed design |
|---|---|
| `cmd_review` auto-branch: `try: _picked=… except: _picked=[]`; `auto_spawn` "best-effort — never blocks"; `persona_overrides` in bare `try/except` | Phase 2 selection **silently collapses to the floor** with zero record. "Why each fired" is not recorded; failures are swallowed. |
| `agent_router.select_agents_for_goal` = word-set intersection, `score>0`, **no grade**. `ratings.json` never written by review. No `usage.jsonl`. | "Graded personas / match×grade / CE floor / epsilon-greedy tail" are **fictional** — grades default to nothing, so "graded" == match-only. Vacuously satisfied. |
| `k=2` hardcoded; sample = `files[:6]` × `2000` chars | "k scales with level" and full-diff coverage are not real. A specialist for an issue in file 7 / past char 2000 is **never selected**. |
| `hreview.py` emits free text, `print(txt[-4000:])`; CLI failure path `return ""`; `_content_ok` only checks for marker strings | Findings are **never machine-readable**. Everything downstream ("for each finding…") has no list to iterate. A `""` or truncated output is indistinguishable from "clean." |
| `.pins.json` = `sha256(body) → source`. No path→plan map. | G1 "resolve owning plan" has **no backing index**. Owner map can be empty and still "resolve." |
| `run_gates.py`: `if not os.path.exists(path): continue`; then `print("regression clean")` | **The headline vacuous-green.** regression-proof / mutation-score / gate-the-glue don't exist in the suite → they're skipped → suite passes. G4 "composes all seven rigor gates" is unwired. |
| The design's "seven rigor gates" ≠ the seven in `run_gates.py` (stale/dups/registry/pristine/lint/docs-drift/env-drift) | Two different suites conflated; G4 claims composition that no code performs. |

---

## B. Every hole, with the deterministic check that closes it

Grouped by phase. **Guard = code in the flow-runner (non-bypassable), not skill judgment.**

### Phase 0 — Intake
- **H1 · Empty target set = vacuous pass.** `git diff` empty / not a repo → zero targets → review of nothing exits green. **Guard:** `assert len(targets) >= 1` else `refuse(reason="empty-target-set")`; record `diff_baseline` as a resolved SHA, not the label `"pins"`.
- **H2 · Unclassified target defaults to nothing.** Classification is best-effort. **Guard:** every target MUST receive exactly one `class ∈ {owned,glue,plan,foreign}`; an unclassifiable target → `refuse`. No implicit default.
- **H3 · `owned` has no owner index (pins are hash→source).** **Guard:** build a deterministic `path → owning_plan` index by matching each target's function-body hashes against `.pins.json` *and* the plan that emits them. A file whose body-hash is pinned but has **no emitting plan** = `orphan-owned` → **refuse under STRICT** (cannot fold upstream to a nonexistent plan). Orphan must never silently degrade to advisory.
- **H4 · thinking level null.** **Guard:** default deterministically to `medium`; write it; never null.

### Phase 1 — Front-end
- **H5 · G1 passes vacuously when there are zero `owned` targets** ("all map" is vacuously true). **Guard:** gate asserts `owned_checked == owned_present` **and** `len(targets) >= 1` (composes with H1).
- **H6 · Y1 analyst downgrades STRICT→advisory to dodge work.** **Guard:** `standard` is set **by code** from `LATHE_STRICT`, not by the analyst. If `LATHE_STRICT=1`, `standard=enforcing` is forced; the Y1 skill may *record rationale* but cannot vote it down. Y1 output is schema-validated `{scope_confirmed:bool, standard, refused}` or the step fails.
- **H7 · Refuse path skips the manifest.** **Guard:** manifest emission is registered at A0 in a `finally`/atexit; process cannot exit (refuse, crash, or pass) without a manifest on disk (see H33).

### Phase 2 — Selection
- **H8 · Blanket `try/except` → silent floor.** **Guard:** remove the swallow. Each stage records `status ∈ {ok, skipped:<reason>, error:<trace>}` into `selection.stages[]`. The **CE floor is asserted post-assembly**: `assert {"correctness","adversarial"} ⊆ lenses` else hard-fail (never advisory). Any stage `error` sets `selection_degraded:true`; under STRICT-high, `error` → refuse.
- **H9 · Fake grades.** **Guard:** `considered[].grade` MUST be `null` unless `usage.jsonl` has ≥1 sample for that persona; `grade_source` recorded (`ratings.json:<n>` or `default`). No fabricated precision; "earned grade" language only when `n≥1`.
- **H10 · Truncated sample hides a specialist.** **Guard:** selection sample must cover **all** target hunks (not `files[:6]×2000`); record `sample_coverage_fraction`. `k = f(thinking_level)` in code. Under STRICT-high, coverage `< 1.0` = gate fail.
- **H11 · Mandatory (config) persona swallowed.** **Guard:** a configured `mandatory` persona that fails to inject → **refuse** (config said MUST), not a print-and-continue.
- **H12 · License-gated fetch silently absent.** **Guard:** every catalog match considered for fetch is recorded with `fetched:true|false` + `reason`; a skip is data, not a swallowed exception.

### Phase 3 — Work (review)
- **H13 · Free-text findings — the central hole.** hreview output is prose, tail-truncated; nothing downstream can iterate "each finding." **Guard:** A3 emits **validated JSON**, one object per finding `{severity, file, symbol, claim, failing_input, fix}`; a code-side parser gates the output. Unparseable → re-run the lens **once** → still unparseable = lens `status:unparseable` = **that lens fails** (cannot silently contribute nothing). Remove the `[-4000:]` slice — findings cannot be dropped by a tail cut.
- **H14 · `""`/clean is indistinguishable from "didn't run."** **Guard:** each lens emits an explicit verdict `{lens, status: reviewed|clean|error, findings:[…], evidence_of_read:[file:line citations]}`. A `clean` verdict MUST carry ≥1 concrete citation quoting real lines (proves the file was read). `status:error` under STRICT fails the run — never passes as clean.
- **H15 · Floor-lens crash, run continues green.** **Guard:** `correctness` and `adversarial` must both reach `status ∈ {reviewed,clean}` **with evidence**; either in `error` ⇒ `outcome` cannot be `pass`.

### Phase 3 — Adversarial-verify (A4, the crux)
- **H16 · Placeholder reproducing case** (`assert True`, `pytest.skip`, doesn't touch the symbol). **Guard (mechanical):** the case must (a) **exercise `file:symbol`** — the symbol appears in the case's collected coverage; (b) contain ≥1 real assertion (AST check for `assert`/`raises`); (c) **fail on current pinned code** via real subprocess exit. Pass on current code ⇒ `not-reproduced` (auto-kill). No assertion / symbol untouched ⇒ `no-case` (advisory, cannot block).
- **H17 · Killed findings leak in as real.** **Guard:** `triage_eligible` is set **by code** from `adversarial_verify.outcome`; only `reproduced` may become `triage:real`. Analyst cannot override.
- **H18 · A4 skipped for some findings** (loop `continue` on synth failure). **Guard:** every `findings[]` row MUST carry `adversarial_verify.ran=true` + captured exit code + case source-hash. A row with `ran=false` = manifest-invalid = run fails validation. No finding escapes verification.
- **H19 · Case written against the already-fixed model** (never actually failed on old). **Guard:** A4 runs the case against **on-disk pre-fix** code; `failed_on_old` captured from the real exit, not asserted by the model.

### Phase 3 — Triage / Fold (Y2/Y3)
- **H20 · Over-dedupe drops real findings.** **Guard:** every `reproduced` id is preserved; `duplicate-of:Fk` requires `Fk` to exist and cover the **same symbol** (code-checked). Findings may be merged-with-provenance, never dropped.
- **H21 · Claimed fold, plan unchanged / wrong test / wrong plan.** **Guard:** code hashes the owning plan before/after and requires (a) content changed, (b) the added test **is the same case** that reproduced in A4 (hash/AST match), (c) it lands in the plan's **test** section, (d) the plan is the resolved owner of that file. Plan unchanged ⇒ fold FAILED, finding stays unresolved.
- **H22 · Claimed glue fix, glue unchanged / test not wired into the suite.** **Guard:** before/after hash on the glue file **and** the reproducing case must be added to a standing test that `run_gates` actually executes (gate-the-glue must *run* the new test, see H24).
- **H23 · Route to advisory-only to dodge the fold under STRICT.** **Guard:** under `enforcing`, a `reproduced` finding on `owned`/`glue` **cannot** have `resolution.mode=advisory-only`; code rejects the combination ⇒ run fails. advisory-only is legal only for `no-case`/`not-reproduced`, or `foreign`/`plan` class, or `advisory` standard.

### Phase 4 — Adversarial gate (A5/G4)
- **H24 · `run_gates.py` `continue`s past missing gates → vacuous green (headline).** **Guard:** compute a **required-gate set per run** from the findings: any folded `owned` finding ⇒ `regression-proof` + `mutation-score` REQUIRED; any glue fix ⇒ `gate-the-glue` REQUIRED. `run_gates` must **fail-closed** on a required gate whose file is missing or that didn't execute — replace `if not exists: continue` with `if required and not exists: FAIL`. Record `required_gates[]` and `ran[]`; `required − ran ≠ ∅` ⇒ run fail.
- **H25 · `failed_on_old` for the wrong reason** (import/syntax/collection error, not the bug). **Guard:** capture pytest outcome *kind*; `failed_on_old` requires an **assertion `failed`**, not `error`. An `error` on old ≠ regression-proof.
- **H26 · Mutation score over an empty mutant set (0/0 = pass).** **Guard:** the mutation gate must generate **≥1 mutant that reverts the fix** (models the bug) and require the added test **kills that specific mutant**. Record `mutants_generated`, `mutants_killed`, `bug_mutant_killed:bool`. Empty mutant set ⇒ fail, not pass.
- **H27 · New test present but not run / passes without asserting the bug.** **Guard:** A5 executes the specific test by **nodeid**; `regression_proof` requires the *same nodeid* `failed` on old pin and `passed` on new pin. Cross-check `test_added.nodeid` == the measured nodeid.
- **H28 · Cross-task regression over an empty sibling set.** **Guard:** record `sibling_plans_checked` and require it `== declared_blast_radius`; `0` checked when siblings exist ⇒ fail.
- **H29 · A5 legitimately skipped (zero owned findings) — but conflated with "review silently produced nothing."** **Guard:** `outcome:pass` with zero findings is allowed **only if** every lens is `reviewed|clean` **with evidence-of-read** (H14) and no lens is `error/unparseable`. Distinguishes genuine-clean from silent-failure.

### Phase 4 — Re-review (A6)
- **H30 · A6 skipped or run against stale (pre-rebuild) files.** **Guard:** A6 runs against the **new pin hash**; assert reviewed-file hash == `rebuilt_pin`. `re_review` absent when findings were resolved = manifest-invalid.
- **H31 · A6 finds a new critical, swallowed.** **Guard:** `re_review.new_critical > 0` forces `outcome != pass` (loop-once-more per policy, else refuse). Cannot report `pass` over an open new critical.

### Phase 5 — Manifest (A7)
- **H32 · Incomplete manifest reads as green.** **Guard:** validate against a required-field list before write; any required field `null` ⇒ write manifest with `outcome:"invalid"` + exit nonzero. Never emit a green manifest with holes.
- **H33 · No manifest on crash/refuse (exception before A7).** **Guard:** emission is a `finally`/atexit registered at A0; a mid-run death flushes a **partial** manifest with `outcome:"error"` + `last_phase`. Flow-runner invariant: **no process exit without a manifest on disk.**
- **H34 · `cost/timing = 0.0` passes as real accounting.** **Guard:** populate from the actual usage-ledger append; if the ledger row wasn't written, `cost=null` + degraded `outcome`, not `0.0`. Verify `usage_ledger_appended` by confirming the line count grew — don't just name the file.
- **H35 · run_id collision overwrites a prior manifest.** **Guard:** `run_id = <ISO-ts>-<sha256(targets+diff_baseline)[:8]>`; write is `O_EXCL`; collision → new suffix, never silent overwrite.
- **H36 · JSON and human render drift.** **Guard:** render is derived from the validated JSON (single source); both written atomically or neither.
- **H37 · "seven rigor gates" unwired / conflated with the `run_gates` seven.** **Guard:** the required-gate set is explicit and per-run (H24); the manifest lists exactly which gates were *required*, *ran*, and their verdict. No claimed composition that isn't wired.
- **H38 · Orphan findings/fixes (traceability).** **Guard — traceability gate:** every `findings[]` row must link to (raised-by lens ∈ selection) → (adversarial_verify case) → (plan/glue diff **or** advisory justification) → (gate verdict). Any missing link ⇒ traceability fail. Closes the chain: no orphan finding, no orphan fix, no gate covering nothing.

---

## C. Hardened workflow (typed; guards inline; this is the implementer's spec)

```
INVARIANTS (flow-runner, non-bypassable):
  I1  no exit (pass|refuse|error) without a manifest on disk        [H7,H33]
  I2  CE floor {correctness,adversarial} present + reviewed         [H8,H15]
  I3  every finding carries adversarial_verify.ran=true             [H18]
  I4  triage:real ⇐ adversarial_verify.outcome=reproduced (code)    [H17]
  I5  required-gate set computed per-run; required−ran=∅            [H24,H37]
  I6  manifest validated vs required-fields before write            [H32]
  I7  standard set by code from LATHE_STRICT; skill cannot lower it [H6,H23]
```

**P0 Intake (code)**
- A0 mint `run_id` (ts+hash, O_EXCL); register manifest flush (I1). Resolve target set; **assert ≥1** [H1]. Classify each target → exactly one class [H2]; build `path→plan` owner index from `.pins.json`+plans [H3]. Set thinking level (default `medium`) [H4]. Record `diff_baseline` as SHA.

**P1 Front-end (code gate + gated skill)**
- G1 owner gate: `owned_checked==owned_present` ∧ `len(targets)≥1`; `orphan-owned`/`foreign` under STRICT → refuse [H3,H5].
- Y1 (skill, gated): scope confirm only; `standard` **forced by code** from LATHE_STRICT [H6]. Schema-valid or fail.

**P2 Selection (code mechanics)**
- A2: `k=f(level)`; sample covers all hunks, record `sample_coverage_fraction` [H10]. Per-stage `status` recorded, **no blanket swallow** [H8]. Post-assembly assert CE floor [H8]. Grades `null` unless `usage.jsonl` sample exists [H9]. Mandatory-persona inject failure → refuse [H11]. Every fetch candidate recorded with reason [H12].

**P3 Work (gated skill → code parse)**
- A3: each lens emits **validated finding JSON** + verdict `{status, evidence_of_read}`; unparseable → 1 retry → fail-lens [H13,H14]. No tail-truncation.
- A4: per finding, author case; code checks **symbol-touched + has-assertion + fails-on-old** → outcome∈{reproduced,not-reproduced,no-case}; `ran=true` mandatory [H16,H18,H19]. Kill/downgrade set by code [H17].
- Y2 (skill, gated): dedupe preserving all ids; `duplicate-of` code-verified [H20].
- Y3 (skill, gated): fold-upstream; code diffs plan (owned) or glue, requires content-change + same-case-as-A4 + landed-in-test-section + correct-owner [H21,H22]. advisory-only forbidden for reproduced owned/glue under enforcing [H23].

**P4 Adversarial gate (code)**
- A5: rebuild owning plan(s) under STRICT; run new test by **nodeid**; `regression_proof` = same nodeid `failed`(assert, not error) on old pin ∧ `passed` on new pin [H25,H27].
- G4: `run_gates` **fail-closed** on required-but-missing/didn't-run [H24]; mutation gate requires ≥1 bug-reverting mutant killed by the new test [H26]; sibling-regression `checked==blast_radius` [H28]; traceability gate [H38]. `outcome:pass` with zero findings only if all lenses `reviewed|clean` with evidence [H29].
- A6: re-review vs `rebuilt_pin` hash [H30]; `new_critical>0` ⇒ not-pass [H31].

**P5 Manifest (code)**
- A7: validate required fields → else `outcome:"invalid"`+nonzero [H32]; cost/timing from real ledger (verify line grew) else `null`+degrade [H34]; JSON+render from single source [H36]. Always emitted (I1).

---

## D. Manifest schema — added required-field & validation semantics

Same shape as proposed, with these **enforced** additions (validator rejects the run to `outcome:invalid` if any are missing/ill-typed):

```json
{
  "schema": "lathe.manifest/2",
  "outcome": "pass|refuse|advisory|invalid|error",   // invalid/error still emit (I1)
  "last_phase": "P0|P1|P2|P3|P4|P5",                  // for crash/partial [H33]
  "intake": { "targets":[{ "path","class","owning_plan|null","pin",
                           "orphan_owned":false }],    // [H2,H3]
              "diff_baseline":"git:<sha>",            // never bare "pins" [H1]
              "thinking_level","strict" },
  "frontend": { "standard":"enforcing|advisory",       // set by code [H6]
                "standard_source":"LATHE_STRICT",
                "refused":{ "is_refused","reason" } },
  "selection": {
    "sample_coverage_fraction": 1.0,                  // [H10]
    "degraded": false,                                 // [H8]
    "stages":[{ "name","status":"ok|skipped|error","reason" }],  // no swallow [H8]
    "ce_floor_asserted": true,                         // [H8]
    "considered":[{ "persona","match","grade":null,    // null unless rated [H9]
                    "grade_source":"default|ratings.json:<n>",
                    "picked","reason" }],
    "fetched":[{ "persona","license","fetched":true,"reason" }] }, // [H12]
  "findings":[{
    "id","raised_by":[...],"severity","location","claim","fix",
    "adversarial_verify":{ "ran":true,                 // MANDATORY [H18]
      "outcome":"reproduced|not-reproduced|no-case",
      "case_nodeid","case_hash","symbol_touched":true,
      "has_assertion":true,"failed_on_old_kind":"failed" }, // not "error" [H25]
    "triage":"real|false|duplicate-of:Fk",             // real⇐reproduced [H17,H20]
    "resolution":{ "mode":"fold-upstream|apply-glue|advisory-only",
      "owning_plan","test_nodeid",                     // == case_nodeid [H27]
      "plan_hash_before","plan_hash_after",            // must differ [H21]
      "regression_proof":{ "failed_on_old":true,"passes_on_new":true,
                           "nodeid_matches":true },     // [H27]
      "advisory_justification":null } }],              // required if advisory [H23]
  "gates":{
    "required":["regression-proof","mutation-score","gate-the-glue",
                "standing-regression","traceability"],  // computed per-run [H24]
    "ran":[...], "results":[
      { "name":"regression-proof","verdict":"pass" },
      { "name":"mutation-score","verdict":"pass",
        "mutants_generated":3,"mutants_killed":3,"bug_mutant_killed":true }, // [H26]
      { "name":"standing-regression","verdict":"pass",
        "sibling_plans_checked":7,"blast_radius":7 },   // [H28]
      { "name":"traceability","verdict":"pass" } ] },   // [H38]
  "re_review":{ "against_pin":"sha256…","residual_findings":0,
                "new_critical":0 },                      // vs rebuilt_pin [H30,H31]
  "models":{ "reviewer","analyst","implementer" },       // no nulls [H32]
  "cost":{ "tokens_in","tokens_out","usd" },             // null-not-0 if no ledger [H34]
  "timing":{ "total_s","per_phase":{...} },
  "usage_ledger_appended":{ "path","lines_added":N },    // verified grew [H34]
  "run_id_write":"O_EXCL"                                 // [H35]
}
```

**The single load-bearing correction:** the design's guarantees (regression-proof, mutation, gate-the-glue, "seven rigor gates composed") are asserted against a `run_gates.py` that *skips missing gates and prints "clean"*. Until `run_gates` is made **fail-closed on a per-run required set** (H24) and findings are **machine-readable** (H13) so A4/A5's reproduce-then-resolve can be *measured from real exit codes* rather than *claimed by a model* (H16/H21/H25/H26/H27), the entire contract passes vacuously green while doing nothing. Those two are the implementer's first tickets.

Relevant paths: `/home/user/lathe/lathe.py` (`cmd_review` L257, `cmd_build` L130), `/home/user/lathe/projects/agentic-harness/hreview.py`, `/home/user/lathe/projects/agentic-harness/qa/run_gates.py`, `/home/user/lathe/projects/agentic-harness/tools/agent_router.py`, `/home/user/lathe/projects/agentic-harness/tools/persona_spawn.py`, `/home/user/lathe/projects/agentic-harness/tools/.pins.json`.