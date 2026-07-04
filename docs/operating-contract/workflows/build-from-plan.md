I have enough grounding. I read the actual `plan_validator.py`, `spec_lint.py`, `strict_mode.py`, `workflows.py`, and the build/pin/assume seams in `lathe.py`/`engine_v2.py`. The critique below is anchored to what the code really does (including two live fail-open bugs). Returning it directly as my output.

---

# Adversarial critique + hardened spec — `lathe build <plan>`

## Part 0 — Three structural vacuities that dwarf the per-step ones

These are cross-cutting; fixing them closes whole classes of holes at once. The implementer should build these FIRST, as spine primitives.

**U1 — Gates fail OPEN on their own errors.** This is not hypothetical. In `spec_lint.py::_stub_survives`, `except Exception: return False` — any sandbox import failure, timeout, or OOM makes every trivial stub read as "did not survive," so `lint_function` returns `blocking=False`, `ok=True`. A spec-lint gate that can't run its probe reports **PASS**. The same fail-open shape lurks in every gate that shells out or imports (`run_gates.py` missing → no regression detected → "green").
- **Deterministic close:** every gate returns a **tri-state** `{PASS, FAIL, INOPERATIVE}`, never a bool. An internal exception maps to `INOPERATIVE`, and under STRICT `INOPERATIVE ≡ FAIL` (refuse). Each gate must run a **canary pair before judging the real subject**: a positive control that MUST pass and a negative control that MUST fail. If either canary misbehaves the probe is declared `INOPERATIVE`. For spec-lint specifically: a known-good impl must pass the tests (positive) and a `return None` stub against a deliberately non-trivial assert must be killed (negative) — only then is a "no survivors" verdict trustworthy. `except` may never `return False`-as-pass.

**U2 — STRICT *defaults* env instead of *clamping* it.** `strict_mode.strict_defaults` only injects a value `if current == ''` (fill-if-empty). So an explicitly-exported `LATHE_MUTATION_SCORE=0.01` (or `LATHE_LINT_SPEC=warn`) **survives STRICT untouched** — directly contradicting the design's claim "a skill cannot lower a gate threshold below the STRICT floor." Today a caller lowers every threshold by pre-setting the env.
- **Deterministic close:** replace fill-if-empty with **clamp-to-floor**. For numeric floors `effective = max(configured, FLOOR)`; for mode enums, STRICT forces the strict value unconditionally (`block`, `1`). The dispatcher computes effective values, records both `configured` and `effective` in the manifest, and **refuses** if any configured value is below floor while claiming STRICT (so lowering attempts are loud, not silently clamped-and-forgotten).

**U3 — The engine is reachable *around* the spine.** `projects/agentic-harness/CLAUDE.md` documents the real bypass: `python engine_v2.py <plan> openai:local 3`. That path pins code and runs regression but **emits no manifest and honors no contract**. Bare `lathe build` routing through the contract is worthless if the engine underneath is a public door.
- **Deterministic close:** the engine's build entry asserts a **contract token** in the environment that only the dispatcher mints (a per-run nonce written to the intake stub); absent → the engine refuses with "run via `lathe build`, not directly." Equivalently, move manifest emission *into* the engine's terminal path so there is exactly one code path and it always emits. Either way: **one entry, no around.**

---

## Part 1 — Per-phase holes → deterministic closes

### Phase 0 — Intake / pin-state

**H1 — Replay trusts the cache (0 gate calls, not just 0 model calls).** The design short-circuits a fully-pinned plan to "byte-identical replay." But `.pins.json` is a mutable file. A pin created under a *weaker past gate regime* (before mutation-score existed), or a hand-edited/poisoned pin, replays as **PASS with nothing re-checked**. "0 model calls" is the goal; "0 gate calls" is the hole.
- **Close:** replay is **re-verification, not trust**. On replay the dispatcher (a) recomputes the module content-hash and requires it to equal the `.pins.json` key, and (b) **re-runs the plan's own tests against the pinned bytes in the sandbox** (cheap, no model). Additionally each pin records the **gate-regime version** it was last verified under; if the current regime is stricter, the pin is *not* honored — it is re-gated. A pin that no longer passes → `outcome=REFUSED(stale-pin)`, not `REPLAYED`.

**H2 — Model alias is not a fingerprint.** Pin key is `spec+tests+"openai:local"`. Two different local weights both aliased `openai:local` collide → a "byte-identical" claim that isn't. 
- **Close:** pin key and manifest record a **model fingerprint** (name + version/weights-digest + endpoint identity), not the alias. Fingerprint mismatch vs the current endpoint invalidates the pin (re-gate).

**H3 — Crash before terminal = no manifest at all.** "Always emitted" holds only on graceful exit. OOM/SIGKILL mid-generate leaves *nothing*, and nothing is indistinguishable from "never ran."
- **Close:** emit an **intake stub manifest atomically before any work** (`outcome=INCOMPLETE`, `status=STARTED`, contract token, cli, plan sha). Terminal write *updates* it. A startup **reconciler** marks any `STARTED` manifest with no terminal update as `CRASHED`. Manifest path is opened `O_CREAT|O_EXCL` so a run can never silently clobber a prior run's record.

### Phase 1 — Assumption audit

**H4 — Empty ledger passes vacuously.** The auditor is an LLM; "found no assumptions" → `blocking_open=0` → gate green with zero work done. Same failure class as "zero adversarial cases."
- **Close:** the assumption gate refuses an empty ledger **unless** the audit emits a **positive coverage attestation**: `audited_pairs == N` where N = plan's `len(FUNCTIONS)`, plus each function id enumerated. Ledger `[]` with no coverage record = `FAIL(no-audit-performed)`, symmetric to the zero-cases guard.

**H5 — Blanket-accept rubber-stamps HIGH items.** The code has a real `accepted N in bulk` path. A HIGH-materiality choice "resolved" by bulk-accept satisfies the gate with no judgment — exactly what the audit exists to prevent.
- **Close:** bulk-accept is **permitted only for LOW/MED**. Every HIGH item requires a per-item decision whose rationale is (a) non-empty, (b) **distinct from the assumption text** (`decision.text != assumption.text`, min length), and (c) not in a boilerplate denylist ("looks fine", "ok"). Manifest stores a rationale hash per HIGH item so a reviewer can see it wasn't a stamp.

**H6 — Stale resolutions.** Resolve HIGH items, then edit the spec → do the old decisions still "count"? `.decisions.md` lives beside the plan; the assumption entry keeps a `digest`.
- **Close:** the `assumption-gate` inside the STRICT bundle recomputes the spec digest at build time and requires `decisions.digest == current_spec_digest`; mismatch → `FAIL(stale-resolution)`. (The `assume` command already keeps decisions only when digests match — the build gate must *enforce* the same check rather than trust the file.)

### Phase 2 — Selection

**H7 — "Selected" ≠ "ran."** A persona listed in `selection.personas` with a plausible `why` can be recorded as satisfying the CE floor while never actually executing. `ce_floor_satisfied: true` is asserted, not proven.
- **Close:** each persona entry requires `ran: true` + a non-empty `output_ref` pointing at a durable artifact (the CE finding file / synth-case file). The floor gate asserts the floor personas have `output_ref`s, not just names. A listed-but-unexecuted persona = `FAIL(floor-not-run)`.

**H8 — Promised `high` specialist silently absent.** At `high`, a domain trigger (auth/token/crypto tokens in the plan) is supposed to fetch a specialist. Fetch failure could downgrade scrutiny silently while the manifest still says `thinking_level: high`.
- **Close:** if a domain trigger fires and the specialist cannot be fetched, that is `REFUSED(specialist-unavailable)` under STRICT, or an explicit `selection.downgraded: {trigger, reason}` that is **itself a gate requiring acknowledgment** — never an invisible drop.

### Phase 3 — Work

**H9 — ARTIFACTS/GLUE plans bypass the entire test-quality + STRICT bundle.** `spec_lint` only extracts `FUNCTIONS`; an ARTIFACTS-only or GLUE plan yields an **empty lint list → zero survivors → "PASS"** vacuously. And `strict_plan_gaps` itself admits STRICT "cannot gate an ARTIFACTS-only plan." So build-from-plan of a non-FUNCTIONS plan skips mutation-probe, mutation-score, and most of the seven gates while reporting green.
- **Close:** record `functions_declared` and `functions_linted` in the manifest; guard: if `FUNCTIONS` present, `linted == declared` or `FAIL`. An ARTIFACTS/GLUE plan under STRICT must route to the artifact/glue gate (script-gated + `gate-glue` exercised) and **must not be allowed to read as PASS on an empty function set** — zero coverage is `REFUSED(unenforceable-under-strict)`, matching the code's own stated limitation instead of papering over it.

**H10 — Mutation probe fail-open** — this is U1 instantiated in the highest-value gate (`_stub_survives`). Called out separately because it is the "are the tests even good?" gate and it currently answers "yes" whenever the sandbox hiccups. Close = U1's canary + tri-state, applied here first.

**H11 — Reused (partial) pins re-validated only against tests, not the current STRICT bundle.** `engine_v2` reuses a pin when `validate(pin, tests)` passes — but `validate` only checks the tests pass, not mutation-score / regression-proof at the *current* threshold. A pin banked at score 0.5 is honored even when the floor is now 0.7.
- **Close:** same as H1 — reused pins carry a gate-regime stamp and are re-gated when the current regime is stricter; the manifest's `generate.per_function` marks `REUSED-PIN` entries with the regime they were verified under.

**H12 — Regression-proof killed by a no-op mutant.** The change-detector mutates code and requires a test to fail. A mutation that produces an AST identical to the original (or semantically identical) makes the test "correctly not fail," which can be misread as a passing change-detector.
- **Close:** each mutant must be verified to **differ from the original** (AST hash ≠) and the gate requires **≥K distinct mutants that the suite actually kills**; a run where no non-trivial distinct mutant could be produced is `INOPERATIVE → FAIL`.

**H13 — Sharpen-loop exhaustion must not fall through to pin.** On `max_repairs` exhausted the flow must reach `M(REFUSED, needs-spec-refinement)`; the pin step must assert **the winner passed the full bundle *this run*** (not a prior run, not a reused pin) before committing the hash.
- **Close:** `pin()` takes the current-run bundle verdict as a required precondition and refuses otherwise; the precondition is a value produced this run, not read from disk.

### Phase 4 — Adversarial synthesis

**H14 — "cases_generated > 0" is the wrong metric; cases can be vacuous.** Six `assert True` / duplicate / always-passing cases satisfy a naive count guard. The design's zero-cases guard is necessary but not sufficient.
- **Close:** the guard counts **effective** cases only. A synthesized case counts iff it (a) parses and **executes** as an assert, (b) is **distinct** (normalized-AST) from every plan test and every other synth case, and (c) has **kill-power** — it FAILS against at least one trivial stub / known-bad mutant. `cases_with_killpower ≥ threshold(level)` is the gate; `cases_generated` is descriptive only. Zero effective cases = `REFUSED(no-adversarial-killpower)`.

**H15 — A synth case that ERRORS (raises, not asserts-false) against the winner must reject, not skip.** Fail-closed on exceptions in the case runner.
- **Close:** case outcome is `{pass, fail, error}`; `error` counts as `fail` (reject candidate). Never `try/except: continue`.

### Phase 5 — Regression + Manifest

**H16 — "Banked but regressed" ships code that breaks a sibling.** The design says a red regression is "banked, run marked regressed." But `engine_v2` already keeps `_pins_snapshot` to *roll back* a bad pin. Under STRICT, banking-anyway is a policy hole that contradicts the code.
- **Close:** under STRICT, regression red → **roll back the pins added this run** (use the existing snapshot), `outcome=REFUSED(regressed)`, `artifact=null`. `REGRESSED`-and-still-shipped is permitted only in casual/non-strict and must be recorded with the specific sibling that broke.

**H17 — Regression gate inoperative reads as green.** `run_gates.py` missing / import error must not equal "no regression."
- **Close:** U1 applied — absent/erroring regression gate = `INOPERATIVE → REFUSED(gate-inoperative)`.

**H18 — Manifest emitted but incomplete reads as fine.** A null `cost_usd`/`tokens` can mean "free" or "never metered"; a missing field can pass unnoticed.
- **Close:** the manifest is **itself gated**. A schema-validation step runs on the manifest before the process exits 0; any missing required field → non-zero exit + `outcome=MALFORMED`. Metering fields are `null` when unmeasured plus a `measured: false` flag; STRICT requires `measured: true`. `0` never masquerades as measured-zero.

**H19 — Pin visible without a durable record.** If the manifest write fails after the pin is published, code shipped with no evidence.
- **Close:** **one transaction** — write pins to staging, write manifest, then atomically publish both (`os.replace`). Manifest-write failure ⇒ pin is not published.

---

## Part 2 — The hardened workflow (implementer spec)

Typed steps: **A**=auto/gated · **G**=gate (tri-state, fail-closed) · **Y**=judgment (LLM output, gated) · **M**=manifest. Every gate returns `{PASS|FAIL|INOPERATIVE}` with a canary pair; `INOPERATIVE≡FAIL` under STRICT. `configured` vs `effective` env recorded; STRICT **clamps** (U2).

```
[0] INTAKE  (code, non-bypassable)
    - assert contract token (U3); reject direct-engine entry
    - mint run_id = ts + plan-sha + pid; write INTAKE-STUB manifest O_CREAT|O_EXCL (H3)
    - resolve plan; classify build-from-plan; read thinking_level
    - model FINGERPRINT resolved, not alias (H2)
    - pin-state = hash(spec+tests+model_fp) vs .pins.json, WITH gate-regime check (H1)
      → all pinned AND regime current → mode=replay ; else mode=build

[1] FRONT-END  A assume → G assumption-gate
    - clarify = "n/a — plan is frozen contract" (recorded)
    - auditor emits ledger + COVERAGE ATTESTATION (audited_pairs==len(FUNCTIONS)) (H4)
    - STRICT: HIGH open → REFUSE; HIGH resolved only via per-item non-boilerplate rationale (H5)
    - assumption-gate rechecks decisions.digest == spec.digest (H6)

[2] SELECTION  (code mechanics + data catalog)
    - decider picks role-fixed set; each persona carries ran/output_ref contract (H7)
    - high + domain-trigger + specialist-unavailable → REFUSE or explicit gated DOWNGRADE (H8)

[3] WORK
    G validate      plan_validator (data-only / import-allowlist / dunder-block)  → refuse→M
    G spec-lint     mutation PROBE w/ CANARY + tri-state (H10/U1);
                    functions_linted==functions_declared; ARTIFACTS/GLUE→artifact gate, no vacuous PASS (H9)
    A generate      best-of-N on implementer, sandbox-gated; STRICT env CLAMPED (U2)
    G STRICT×7      test-ack · regression-proof(distinct-mutant ≥K, H12) · mutation-score(≥effective floor)
                    · gate-glue · test-kind · assumption-gate(digest-fresh) · criteria-traceability
                    reused pins re-gated under CURRENT regime (H11)
    Y/A sharpen     analyst rewrites SPEC/tests only, ≤max_repairs; exhausted → REFUSE(needs-spec-refinement) (H13)

[4] ADVERSARIAL GATE
    G synth         adversarial+testing(+domain@high) author NEW cases; run vs winner
                    guard: cases_with_KILLPOWER ≥ threshold (distinct, executing, mutant-killing) (H14)
                    case error ≡ fail (H15); zero effective cases → REFUSE
    A pin           precondition: winner passed THIS-run bundle (H13); correctness floor read;
                    content-hash spec+tests+model_fp → STAGING (not published yet)

[5] REGRESSION + MANIFEST
    G regression    run_gates.py, canary'd; INOPERATIVE→REFUSE (H17);
                    STRICT red → ROLLBACK pins-this-run, REFUSE(regressed) (H16)
    G manifest-schema  validate required fields; missing → exit≠0, outcome=MALFORMED (H18)
    M publish       transaction: staged pins + manifest published atomically; manifest-fail ⇒ no pin (H19)
```

**Replay path (mode=replay):** `[0] → re-hash + re-run plan tests vs pinned bytes in sandbox (H1) → G regression → G manifest-schema → M(REPLAYED)`. Zero model calls, **non-zero gate calls.** A pin that fails re-verification → `REFUSED(stale-pin)`.

**Thinking-level dial (now clamped):** casual/medium/high map to `LATHE_TRIES` 1/3/5–8, `mutation-score` effective-floor `max(configured, {0.5,0.5,0.7})`, synth `cases_with_killpower ≥ {1,3,5}`, selection {floor / +0 / +1 fetched specialist}. A skill may *raise* a level; the clamp forbids lowering any effective value below the STRICT floor (U2).

---

## Part 3 — Hardened manifest schema (superset; new/changed fields marked ★)

```json
{
  "schema_version": "2",                                   // ★ manifest is itself gated (H18)
  "status": "STARTED|TERMINAL",                            // ★ intake stub written first (H3)
  "run_id": "2026-07-04T..-<pid>-<plan-sha8>",
  "contract_token": "<nonce>",                             // ★ proves spine entry (U3)
  "invocation": "build-from-plan",
  "cli": "lathe build examples/ledger/ledger_core.py",
  "plan": {"path":"...","sha256":"...","functions_declared":5,"mode":"build|replay"},
  "thinking_level": "medium",
  "env": {"strict": true,                                  // ★ configured vs effective (U2)
          "clamped": [{"key":"LATHE_MUTATION_SCORE","configured":"0.01","effective":"0.5","action":"floor-refused|clamped"}]},

  "intake": {"pin_state":"partial","pinned_fns":2,"to_build":3,
             "model_fingerprint":{"alias":"openai:local","name":"...","version":"...","digest":"sha256:..."}}, // ★ H2

  "front_end": {
    "clarify": "n/a — plan is frozen contract",
    "assumption_audit": {"ran": true, "persona":"assumption-auditor",
      "audited_pairs": 5, "coverage_complete": true,       // ★ H4 (== functions_declared)
      "ledger":[{"item":"...","materiality":"HIGH","status":"resolved",
                 "decision_ref":"ledger_core.py.decisions.md#3",
                 "rationale_hash":"sha256:...","bulk_accepted":false}], // ★ H5
      "decisions_digest_match": true,                      // ★ H6
      "blocking_open": 0 } },

  "selection": {
    "personas":[{"name":"correctness-reviewer","phase":"pin","why":"CE floor",
                 "ran":true,"output_ref":"docs/ce/<run>.correctness.json","grade":0.0}], // ★ ran+output_ref (H7)
    "ce_floor_satisfied": true,
    "downgraded": null                                     // ★ or {trigger,reason} (H8)
  },

  "work": {
    "validate":{"verdict":"PASS"},
    "spec_lint":{"verdict":"PASS","canary_ok":true,        // ★ probe canary (U1/H10)
                 "functions_linted":5,"functions_declared":5, // ★ H9
                 "static_gaps":[],"stub_survivors":[]},
    "generate":{"tries":3,"per_function":[
        {"fn":"post","result":"PASS","tier":"local","try":2,"gate_regime":"2"},
        {"fn":"audit","result":"REUSED-PIN","tier":"pin","gate_regime_verified":"2","regated":true}]}, // ★ H11
    "strict_gates":{"test-ack":"PASS","regression-proof":{"verdict":"PASS","distinct_mutants_killed":4}, // ★ H12
        "mutation-score":{"verdict":"PASS","score":0.83,"effective_threshold":0.5},
        "gate-glue":"PASS","test-kind":"PASS","assumption-gate":"PASS","criteria-traceability":"PASS"},
    "sharpen_loop":{"spec_rewrites":0,"exhausted":false}    // ★ H13
  },

  "adversarial_gate": {
    "ran": true,
    "cases_generated": 8, "cases_with_killpower": 6, "cases_duplicate": 2, // ★ H14
    "cases_passed": 6, "cases_errored": 0,                 // ★ error≡fail (H15)
    "authors":[{"name":"adversarial-reviewer","ran":true,"output_ref":"..."}],
    "rejected_candidates": 0
  },

  "pins":[{"fn":"post","pin":"sha256:...","inputs":"spec+tests+model_fp","gate_regime":"2","published":true}], // ★ staged→published (H19)
  "replay_verification": {"reran_tests": true, "hash_match": true, "verdict":"PASS"}, // ★ replay is re-verify (H1)
  "regression":{"gate":"run_gates.py","canary_ok":true,"verdict":"PASS","rolled_back":false,"broke_sibling":null}, // ★ H16/H17

  "models":{"implementer":"...","analyst":"...","adversary":"..."},
  "metering":{"measured":true,                             // ★ null≠0 (H18)
    "tokens":{"programmer_local":{"prompt":0,"eval":0},"analyst":{"prompt":0,"eval":0}},
    "cost_usd":0.0},
  "timing_ms":{"total":0,"generate":0,"synth":0,"gates":0},

  "outcome":"PASS|REFUSED|REGRESSED|REPLAYED|CRASHED|MALFORMED", // ★ +CRASHED/+MALFORMED (H3/H18)
  "refusal":{"phase":"spec-lint","gate":"mutation-probe","reason":"stub 'return a[0]' survived all tests","inoperative":false}, // ★ inoperative flag (U1)
  "artifact":"projects/.../ledger_core.py"                 // null on any non-PASS
}
```

## Part 4 — Guards catalog (the code-side, non-bypassable set)

Universal: **(G0)** tri-state gates, no exception→PASS, canary pair per gate (U1); **(G1)** STRICT clamps not defaults, floor-violation refuses (U2); **(G2)** engine refuses without contract token — one entry (U3); **(G3)** intake stub before work + orphan reconciler (H3); **(G4)** manifest is schema-gated and published in one transaction with the pins (H18/H19).

Invocation-specific: **(G5)** replay re-runs tests vs pinned bytes + regime check — no trust-the-cache (H1); **(G6)** empty assumption ledger fails unless coverage-attested (H4); **(G7)** HIGH assumptions need per-item non-boilerplate rationale, no blanket accept (H5); **(G8)** persona counts only with `ran+output_ref` (H7); **(G9)** `functions_linted==declared`, ARTIFACTS/GLUE cannot vacuously PASS (H9); **(G10)** reused pins re-gated under current regime (H11); **(G11)** adversarial guard counts kill-power cases, error≡fail (H14/H15); **(G12)** STRICT regression-red rolls back and refuses (H16).

**Bottom line:** the original design is correct about *what* to enforce but repeatedly assumes gates and the manifest can't themselves fail, be pre-weakened, be bypassed, or pass on zero/vacuous work. The three live openings in this repo are the fail-open `_stub_survives`, the fill-not-clamp `strict_defaults`, and the documented direct-`engine_v2.py` entry — fix those plus the tri-state/canary/transaction primitives and the remaining per-phase holes collapse into a uniform "no gate may pass without doing, and proving it did, its work."