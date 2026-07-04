Grounded in the four sources. My critique below cites the real gate mechanics (`GATES_REFERENCE.md` §1.0–2.7, the `GATES_STRESS_TEST.md` fail-open findings F1–F8), the six-phase spine (`OPERATING_CONTRACT_DESIGN.md`), the step-typing in `projects/agentic-harness/tools/workflows.py`, and the CE-floor rule in `PERSONAS.md`.

---

# Adversarial critique of `gate-quality` — and the hardened spec

## The load-bearing flaw the draft did not close: the recursion

The draft correctly makes per-gate verdicts tri-state so a no-op gate can't report green. Then it builds a meta-gate to check that — **and leaves the meta-gate itself vacuously satisfiable.** Every "gate-the-gates" assertion in step 5 is a `∀` over `gate_set`; a `∀` over an empty or under-scoped set is trivially true. The draft fixed the bug one level down and re-committed it one level up. It also trusts each gate to *self-report* `precondition_met`/`ran` — the same locus that historically reported green (F3, F4). The fix is a small set of **code invariants that read raw evidence numerics, not self-reports, and that fail closed on absence.**

Below: every hole where a step can be skipped, produce nothing, emit an incomplete manifest, or pass vacuously — each with the deterministic check that closes it.

---

## Holes and their deterministic closures

**A — Empty/under-populated `gate_set` = green over nothing.** Scope resolver returns `[]` (plan with no functions, typo'd target, "no applicable gates") → "every requested gate ran" is vacuously true, `vacuous_passes:[]`, `overall:PASS`, `pass_count:0`. Identical to the original bug.
- *Check:* `assert len(gate_set) >= 1 and len(targets) >= 1` else `ERROR`/exit 2. **Accounting identity:** `pass + fail + inconclusive + error == len(gate_set) × len(targets)`, asserted at close. **`overall==PASS` requires `pass_count >= 1`** — you cannot PASS having produced zero verdicts.

**B — Scope resolver silently narrows the work.** Autonomous "resolve by deterministic default" picks `gate_set = standing gates` for a target that is a shippable FUNCTIONS plan → 7 tree-hygiene gates pass, zero test-adequacy gates run, plan reported gate-clean. The resolver is where the work gets defined away.
- *Check:* resolver is **total and computes the applicable universe from target type** (FUNCTIONS plan → build-time battery applicable; tree → standing). Assert `gate_set ⊇ applicable_mandatory`, OR every applicable-but-excluded gate is materialized in `gates[]` as `ran:false, verdict:INCONCLUSIVE, reason:"out-of-scope"`. Excluded applicable gates can never vanish. Manifest: `resolved_scope.excluded_applicable[]`.

**C — `precondition_met` is self-reported (F3/F4 class).** Step 5 trusts each gate wrapper's `ran`/`precondition_met` flag. A lazy wrapper returning `ran:true` on a no-op is indistinguishable from a real run — the exact self-certification that failed in test-kind and assumption gates.
- *Check:* the runner **independently re-derives vacuity from evidence numerics the gate cannot influence**, one predicate per gate:
  - mutation-score → INCONCLUSIVE iff `evidence.total == 0` (per `GATES_REFERENCE.md` §1.4 "no mutants → no-op").
  - spec-lint → INCONCLUSIVE iff target has 0 test asserts or `stubs_probed == 0` (§1.3).
  - regression-proof → INCONCLUSIVE iff `old_code is None` (§1.2 "first build has nothing to regress against").
  - lint_no_real_bugs → INCONCLUSIVE iff `shutil.which('ruff') is None`, probed *by the runner* (§2.5 "skips cleanly if ruff absent" — that skip is the fail-open).
  - registry → INCONCLUSIVE iff registry empty/absent (§2.3 "empty registry passes").
  - test-kind → INCONCLUSIVE iff `required_kinds == []` (§1.6). test-ack → INCONCLUSIVE iff no functions to hash. gate-the-glue → INCONCLUSIVE iff no GLUE present.
  - A gate whose `evidence` omits the numeric its predicate reads is itself INCONCLUSIVE (`reason:"evidence-incomplete"`). Evidence carrying the numeric is a **required** manifest field.

**D — "always emitted" dies on `kill -9` / a hung lens call.** A `finally`-block emit does not survive SIGKILL, OOM, or a hung network call. Absent manifest = the ultimate incomplete manifest; a consumer that reads "no file" as "not yet run" fails open.
- *Check:* write a **skeleton manifest at step 0, before any work**, pre-stamped `overall.verdict:"ERROR", exit_code:2, closed:false`. Every step updates in place via append-journal + atomic rename. Death leaves an on-disk ERROR record = fail-closed by construction. Per-step `wall_deadline`; a lens/probe exceeding it is killed and recorded `INCONCLUSIVE(timeout)`. Manifest: `manifest_lifecycle:{opened_at, last_step, closed}`; consumers treat `closed:false` as untrusted.

**E — Lens step produces nothing, read as "clean" (and the citation-gate silently drops).** Casual skips step 6; in medium+, an analyst returning `findings:[]` is indistinguishable from "ran, all clear." Worse, "each finding must cite a verdict+numeric or it's dropped" turns a sloppy/adversarial model that emits uncited findings into `findings:[]` = false green.
- *Check:* distinguish `findings_ran:false` (skipped) from `findings:[]` (ran, cited nothing). **Coverage rule:** every FAIL/INCONCLUSIVE/WARN verdict must be either cited by ≥1 finding OR explicitly `acknowledged_benign` by a lens with a reason; an uninterpreted non-PASS verdict → meta-gate INCONCLUSIVE (`reason:"non-pass verdict not interpreted"`). Dropped findings are **not** silently discarded — recorded in `findings_rejected[]` with drop reason; `len>0` is a lens-quality WARN. Manifest: `findings_ran`, `findings_rejected[]`, `uninterpreted_verdicts[]`.

**F — the read-only guard is either vacuous or breaks the high-tier probe.** spec-lint's stub-probe and mutation-score *execute* code (§1.3/§1.4); under `LATHE_SANDBOX=inproc` that's arbitrary code in-process. The high-tier planted-defect probe *mutates the target*. A naive `tree-hash-unchanged` guard trips on the probe; a loose one lets sandbox writes through.
- *Check:* define read-only precisely = **canonical `plans/`+`tools/`+pins byte-identical before/after.** Snapshot content-hash at step 0, assert equality at close. The planted-defect probe operates only on a scratchpad copy; assert it never touched the snapshot set. Force `LATHE_SANDBOX != inproc` for gate-quality (subprocess/docker isolation) or record `sandbox:inproc` as a HIGH assumption. Manifest: `read_only_proof:{tree_hash_before, tree_hash_after, equal}`.

**G — the fail-open-tolerance assumption is auto-resolved to the unsafe value under posture ambiguity.** §1 auto-resolves the one HIGH assumption to a posture default. Note the STRICT-composition rule (`GATES_REFERENCE.md` §Part 3): **empty-string `LATHE_STRICT` is treated as unset.** So an ambiguously-configured autonomous run silently resolves to `advisory`, and every INCONCLUSIVE exits 0 — the silent guess the assumption-gate exists to forbid (F4).
- *Check:* fail-open tolerance **ties to `fail-closed` whenever `LATHE_STRICT` is empty/unset/garbled** (mirror the v2.9.0 issue-#6 fail-closed materiality fix). Autonomous auto-resolution may only pick the fail-closed value; resolving to `advisory` requires explicit non-empty `LATHE_GATE_ADVISORY=1`, logged. Refuse (ERROR) if an auto-resolution would relax posture without that opt-in. Manifest: `assumptions[].{auto_resolved, direction:"fail-closed"}`.

**H — CE-floor guarantees *selection*, not *execution*.** `PERSONAS.md`: the floor guarantees adversarial is *selected*. The decider selects it, step 6 is skipped at casual, the meta-interpretation never runs. "Selected" ≠ "fired." Also `testing` only fires on `gate_set ∩ {test gates}`; a standing-only scope leaves a plan's test-adequacy INCONCLUSIVEs uninterpreted.
- *Check:* the adversarial **meta-gate is step 5 = CODE**, structurally never gated behind a persona — the vacuous-pass check runs regardless of lens firing. Track three states per lens: `selected / fired / produced_output`. Assert `adversarial.fired == true` on every non-casual run; selected-but-not-fired → meta-gate INCONCLUSIVE. Manifest: `selection.lenses[].{selected, fired, findings_count, skipped_reason}`.

**I — high-tier "strict-sim" and "planted-defect probe" invert vacuously.** "Report which gates WOULD fail under STRICT": a gate the sim can't instantiate reports nothing → reads as "would pass." The planted-defect probe ("mutate target, assert gate catches it"): if mutation yields 0 mutants, there's no defect, so "gate caught it" is vacuously true → the gate is certified self-guarding having faced nothing.
- *Check:* probe asserts **it actually planted first**: `assert defect_injected` (mutant differs from original AND parses/runs) else `planted_defect_probe = INCONCLUSIVE`, never PASS. Strict-sim: every applicable STRICT gate that couldn't instantiate is `sim_result:INCONCLUSIVE`, never omitted; `assert len(sim_results) == len(strict_applicable)`. Manifest: `planted_defect_probe:{planted, gate_caught}`, `strict_sim[]` with one entry per applicable gate.

**J — provenance fields nullable → the evaluation instrument silently degrades.** `timing.per_gate_ms`, `tokens`, `cost_usd`, `models[]` are schema-listed but nothing forces population. A null-timing gate still "emits" a manifest. The priority deliverable is unevaluatable and nobody notices.
- *Check:* **schema-validate the manifest against a required-fields JSON Schema before close.** Every `gates[]` entry MUST have non-null `{verdict, reason, evidence, ran, precondition_met, config_source, impl, timing_ms}`. `models[]` non-empty iff any lens fired; `tokens`/`cost_usd` non-null iff `models[]` non-empty. Schema failure → `overall.verdict:ERROR` (you cannot emit a green manifest that is itself malformed). Manifest: `schema_valid`, `schema_version`.

**K — a relaxed threshold passes as a clean pass.** `config_source` is recorded but never compared to the STRICT baseline. Someone sets `LATHE_MUTATION_SCORE=0.05`, the gate PASSES at 0.06 kill-ratio, `config_source` obscures that it ran below §1.4's 0.5 baseline. A relaxed gate passing is a vacuous pass in disguise.
- *Check:* record both `effective_threshold` and `strict_baseline`; if `effective` is weaker, `relaxed:true`, and under strict posture degrade PASS→WARN/INCONCLUSIVE (`reason:"ran below STRICT baseline"`). Manifest: `gates[].{effective_threshold, strict_baseline, relaxed}`.

**L — `all_requested_ran` is one bool over gates, losing per-(gate,target) cells.** A gate that ran on target A but errored on B can still flip the aggregate true. Per-cell completeness is invisible.
- *Check:* materialize the full `gate × target` matrix at step 1; every cell terminates in exactly one verdict; `assert unset_cells == []` at close. Manifest: `coverage_matrix:{expected_cells, resolved_cells, unset_cells[]}`; non-empty `unset_cells` → ERROR.

**M — `exit_code` and `overall.verdict` are independently assigned and can drift.** CI keys on exit code; a bug setting `verdict:REFUSE, exit:0` is a silent fail-open in automation.
- *Check:* `exit_code` is a **pure function of the verdict counts, computed once**, and `overall.verdict` is derived from the same function: `0` iff `fail==0 and (inconclusive==0 or posture==advisory)`; `1` iff `fail>0`; `2` otherwise. Assert consistency as the final statement.

**N — a nonexistent/unreadable target has "no applicable gates" → PASS.** A misspelled plan path resolves to a target with an empty applicable set → collapses into Hole A.
- *Check:* per-target precondition `assert exists and readable` at step 1; a nonexistent target is `ERROR`, never absorbed as "nothing to gate."

---

## Hardened workflow (implementer's spec)

**Invariants — non-bypassable code in the flow-runner, none overridable by a skill:**

- **INV-0 (skeleton-first):** manifest opened at step 0 as `ERROR/closed:false` before any work; atomic in-place updates; closed only by the exit function.
- **INV-1 (non-empty scope):** `len(gate_set)≥1 ∧ len(targets)≥1`, else ERROR.
- **INV-2 (coverage matrix):** every `gate×target` cell resolves to exactly one of {PASS,FAIL,INCONCLUSIVE,ERROR}; `unset_cells==[]`.
- **INV-3 (independent vacuity):** vacuity derived by the runner from evidence numerics (Hole C predicates), never from gate self-report; missing numeric → INCONCLUSIVE.
- **INV-4 (PASS floor):** `overall==PASS` requires `pass_count≥1 ∧ inconclusive==0 ∧ fail==0` (or advisory posture for the inconclusive term).
- **INV-5 (posture fail-closed):** posture tie-breaks to `strict`/`fail-closed` on empty/unset/garbled `LATHE_STRICT`; relaxing requires explicit `LATHE_GATE_ADVISORY=1`.
- **INV-6 (read-only proof):** canonical tree+pins hash equal before/after; probes confined to scratchpad.
- **INV-7 (schema-valid):** manifest passes required-fields schema before close, else ERROR.
- **INV-8 (exit purity):** exit code = pure function of verdict counts, equal to `overall.verdict`.
- **INV-9 (lens coverage):** every non-PASS verdict cited or explicitly `acknowledged_benign`; uncited/uninterpreted → INCONCLUSIVE; dropped findings recorded, not discarded.

**Steps (A=auto/G=gate/Y=you/M=manifest):**

| # | Type | Step | Hardening added |
|---|---|---|---|
| 0 | A | Intake | Mint run_id, **open skeleton manifest (INV-0)**, snapshot tree hash (INV-6), resolve posture fail-closed (INV-5). |
| 1 | A | Scope resolve | Compute applicable universe per target-type; **build gate×target matrix (INV-2)**; per-target exists/readable (Hole N); materialize excluded-applicable as INCONCLUSIVE (Hole B); assert non-empty (INV-1). |
| 2 | A | Assumption-audit | Emit fail-open-tolerance assumption; auto-resolve **only fail-closed** unless `LATHE_GATE_ADVISORY=1` (INV-5, Hole G). |
| 3 | A | Selection | Decider picks lenses; record `selected` per lens; CE floor forces adversarial *selection*. |
| 4 | A | Run gates | Per cell, capture rich verdict + **required evidence numeric**; runner (not gate) stamps `ran`/vacuity via INV-3; record `effective_threshold`/`strict_baseline`/`relaxed` (Hole K); per-gate `timing_ms`. |
| 5 | G | Gate-the-gates (code) | INV-2/3/4 + relaxed-threshold degrade (K); high-tier planted-defect probe **asserts planted before caught** (Hole I); strict-sim one entry per applicable gate. Runs regardless of lens firing (Hole H). |
| 6 | Y | Lens interpretation | `adversarial.fired` asserted non-casual (H); **coverage rule INV-9**; `findings_rejected[]` recorded; `findings_ran` vs `findings:[]` distinguished (Hole E); per-step deadline (D). |
| 7 | M | Manifest close | Schema-validate (INV-7), compute exit purely (INV-8), assert read-only proof (INV-6), flip `closed:true`. Runs even on partial/ERROR — skeleton already on disk. |

**Manifest fields added on top of the draft schema (all required unless noted):**

```
manifest_lifecycle:{opened_at, last_step, closed}          # INV-0/D
schema_valid, schema_version                               # INV-7/J
resolved_scope.excluded_applicable[]                       # B
coverage_matrix:{expected_cells, resolved_cells, unset_cells[]}   # L/INV-2
read_only_proof:{tree_hash_before, tree_hash_after, equal} # F/INV-6
gates[].{ evidence(with the numeric its vacuity predicate reads),
          effective_threshold, strict_baseline, relaxed,   # K
          timing_ms, ran, precondition_met }               # C/J
meta_gate.planted_defect_probe:{planted, gate_caught}      # I
meta_gate.strict_sim[]  (one entry per applicable STRICT gate)    # I
selection.lenses[].{selected, fired, findings_count, skipped_reason}  # H
findings_ran (bool)                                         # E
findings_rejected[]:{note, drop_reason}                     # E
uninterpreted_verdicts[]                                    # E/INV-9
assumptions[].{auto_resolved, direction}                   # G
overall.{verdict, exit_code}  # exit_code == f(counts), asserted equal   # M/INV-8
```

**The single property to test by executable probe (the method that caught F1–F8):** construct a target with an empty `gate_set`, a target whose only gate is a 0-mutant mutation-score, and a lens that returns uncited findings — assert all three yield `overall != PASS` and `exit != 0`. If any reports green, the recursion is still open.