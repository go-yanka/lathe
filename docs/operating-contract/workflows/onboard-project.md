I have the grounding I need. The proposal's guards are described in prose, but I traced how the real flow runner actually decides pass/fail — and it decides on `rc==0` plus stdout substring-scraping (`flow_report.classify_step`), with gates that silently skip missing checks (`run_gates.py`). That's the soil every vacuous pass grows in. Here is the adversarial critique and hardened spec.

---

# Adversarial critique — `onboard-project`

## Part 0 — Root-cause spine defects (these make EVERY step skippable; cite before per-step)

The proposal assumes "auto = gated on success" and "gate = must pass" are strong. In the real code they are not. Three primitives leak, and every hole below is an instance of one of them.

**D1 — Vacuous pass on empty output.** `flow_report.classify_step` (`tools/flow_report.py:4-18`): a step is `'pass'` iff `rc==0` and no failure-signal substring appears in stdout. An `auto` step that does *nothing*, writes no file, and prints nothing exits 0 → **pass**. Every `auto` in the workflow inherits this.
*Fix (structural):* replace stdout-scraping with a **postcondition registry**. `POSTCONDITIONS[step_id] = predicate(run_dir, manifest) -> (ok, evidence)`. The runner requires `rc==0 AND postcondition.ok AND evidence non-empty`. A step with no registered postcondition is a **config error that refuses the run**, not a free pass.

**D2 — Prose failure-detection is spoofable both ways.** Same function: a step printing `"no errors"` passes; a legit `review` step whose findings text contains `"error:"` *falsely blocks*. Truth cannot live in stdout prose.
*Fix:* each subcommand writes `<run_dir>/steps/<step_id>.result.json` `{status, audit_ran_token, postcondition_hash, evidence}` and exits nonzero on its own failure. The runner trusts the structured record + the postcondition predicate; it never greps prose.

**D3 — Missing gate = silently skipped.** `qa/run_gates.py:26-27`: `if not os.path.exists(path): continue`, and an empty/all-missing `CHECKS` prints `"regression clean (0 checks)"` and **exits 0**. So "standing gates GREEN" can be green over *zero* checks. This is the single most dangerous vacuity in the whole design because it's the final safety net.
*Fix (code change in the vendored file):* a declared-but-missing check script is a **FAIL**, not `continue`; `checks_run==0` or `checks_run < floor` → **exit nonzero**; cross-check `CHECKS` against a `REQUIRED_CHECKS` manifest so a check can't be silently dropped.

**D4 — `you`/`todo` never blocks the verdict.** `flow_report.workflow_verdict:20-31`: only `'blocked'` yields BLOCKED; `'todo'` (every `you` step) and an empty status list both yield **PASS**. The proposal's one `you` step (analyst authors first plan) is therefore unguarded, and a run with all-skipped steps verdicts PASS.
*Fix:* no `you` step may be terminal or unguarded — each is immediately followed by a `gate` that validates its output artifact (added below). `workflow_verdict` over an empty/short status list must FAIL (a run that executed fewer than `len(steps)` contributors is incomplete, not clean).

**D5 — Manifest is a STEP, so a crash before it emits nothing.** The proposal makes `manifest {run_id}` the last step. Any exception in steps 0-16 never reaches it → the "ALWAYS emitted, even on refuse" guarantee is false. The manifest is the evaluation instrument; it must be the *most* robust thing, not the *last*.
*Fix:* emission is a **dispatcher `finally`**, not a step. The manifest object is built incrementally as each phase completes; on any exception or hard-gate refuse it flushes the partial with `verdict="refuse"`, `refusal_reason=<failed phase/gate>`. Remove `manifest` from the step list.

**D6 — "Model ran" is unprovable from output.** clarify/assume/review can return an empty ledger/finding-set that is indistinguishable from "the model was never called." Empty ≠ clean.
*Fix:* every model-work step emits an **`audit_ran` provenance token** = hash over `(real_step_input, model_id, prompt_id, timestamp)`. Absent/empty/stale token → the following gate FAILS. This is what makes "auditor found nothing" distinguishable from "auditor didn't run."

**D7 — No halt-on-red.** Undefined whether a failed mid-flow gate stops the run. If it doesn't, later steps run on a broken foundation and the manifest reports a mix.
*Fix:* gates are typed `hard|soft`. First **hard** fail sets `verdict=refuse`, records the gate, **skips remaining WORK steps**, and drops to the phase-5 finally. No step executes past a red hard gate.

---

## Part 1 — Per-step holes → deterministic check that closes each

| # | Step (proposed) | How it's SKIPPED / NOTHING / VACUOUS | Deterministic check that closes it |
|---|---|---|---|
| 1 | **Target guard** (G0) | Only checks `listdir==[]`. Passes on: name with `../` traversal, absolute path, symlink target, name colliding with an existing project/config, or an empty dir inside a **dirty git tree**. | `TARGET-GUARD` (ALL must pass, unknown=fail): (a) name matches `^[a-z0-9][a-z0-9._-]{0,63}$`; (b) `realpath(target)` is a strict prefix-child of `projects/`; (c) not-exists OR (isdir AND empty); (d) `git status --porcelain <target>` empty; (e) no existing WORKFLOWS/registry/config entry for `<name>`. Record all 5 sub-verdicts. |
| 2 | **Intake interview** (S1) + completeness (G1) | File `CLARIFIED_SETUP.md` written with blank/placeholder fields, or the model silently fills endpoints with a public default URL. "Unknown endpoint fail-closed" has no operational predicate. Interview asks 0 questions. | Parse **CLARIFIED_SETUP.json** (structured, not prose). `INTAKE-COMPLETENESS`: every schema-required key present, typed, non-empty; each endpoint carries `source` and `source != "default"` (a defaulted endpoint can't masquerade as chosen); reject any endpoint host on a public/frontier **denylist** unless `license_posture` explicitly authorizes BYO-remote; `first_units` non-empty; `stack` in known set or `other:<text>`; `len(questions) >= MIN` and every required field traces to an answer id; `audit_ran` token valid. |
| 3 | **Setup assumption audit** (S2) — **NO GATE in proposal** | It's an `auto` step; empty ledger → rc 0 → vacuous pass (D1). Auditor can silently omit the *dangerous* item (public bind) and still "pass". Blanket-accept. | **INSERT gate** `SETUP-ASSUMPTION-GATE`: parse `decisions.json`; assert (a) `audit_ran` token valid (auditor actually ran on the real setup); (b) the **4 required-risk postures** — public/non-local bind, unvetted model license, no data-quality gate, off-machine data path — each appear with `addressed=true` (auditor can't skip the scary one); (c) every `materiality=HIGH` item has resolution ∈{accept,alternative,intent} with a **distinct non-empty rationale** — reject if all HIGH items share one identical resolution string (no blanket accept). |
| 4 | **Selection** (S3) — **NO GATE in proposal** | `select_agents_for_goal` (`agent_router.py:59-74`) returns `[]` on zero keyword overlap → **zero personas**, rc 0 → vacuous pass. "CE floor" and "security-reviewer if PII" are prose, not code. | **INSERT gate** `SELECTION-FLOOR`: from `selection.json` assert (a) `correctness-reviewer` AND `adversarial-reviewer` present **by name** (not by score); (b) `security-reviewer` present **iff** intake flags auth/PII (read from parsed CLARIFIED_SETUP, not model discretion); (c) every pick `license_ok(lic)==True` (fail-closed; `agent_router.py:53`), and any `fetched=true` had its license checked **before** fetch; (d) each pick's `why` non-empty AND references a concrete stack token / intake flag; (e) the 2 unlicensed catalog personas absent; (f) set non-empty. |
| 5 | **Scaffold** (S4) + cleanliness (G2) | Config written with literal `{name}`/empty endpoint; vendored sha recorded as `"unknown"`; NOTICE/CREDITS created empty. G2 delegates to stale_gate which, on a fresh tree, may not exist yet → **D3 silent skip** → vacuous green. | `SCAFFOLD-POSTCOND`: each declared dir exists; `lathe.config.json` parses and each endpoint **byte-equals** the CLARIFIED_SETUP value (reject any value matching `{.*}` or empty); vendored Lathe sha is 40/64-hex and **recomputed in code** from the vendored tree == recorded (don't trust the field); NOTICE.md/CREDITS.md exist and non-empty. Cleanliness must **invoke stale_gate directly and treat a missing script as FAIL** (D3). |
| 6 | **selftest** (S5) + PASS (G3) | "Live probe" satisfied by a localhost that answers 200 but isn't the configured model; a cached/mock capability; 503-loading counted as pass or retried forever. | `SELFTEST-PASS`: from `selftest.json` assert both endpoints did a **live round-trip that echoes the configured `model_id`** (canary catches "wrong endpoint answered"); 503 → **bounded** retry (N cap), exhausted → **FAIL** (not pass, not infinite); every capability in the REQUIRED list present and `pass=true`; result.json well-formed (absent/malformed = fail-closed). |
| 7 | **Analyst authors first plan** (Y1) — `you`, unguarded (D4) | Produces no plan / a malformed plan / a plan that builds something the intake never asked for; `you` never blocks (D4); next step errors or vacuously passes. | **INSERT gate** `FIRST-PLAN-VALID` (uses existing `plan_validator`/`spec_lint`): plan(s) exist and import cleanly; each declares CRITERIA, ≥4 asserts, declared test KINDS; functions pure; **target functions == intake.first_units** (traceability — reject a plan that builds off-brief). |
| 8 | **First-plan assume** (S6) | Same as #3 — empty ledger passes vacuously. | **INSERT gate** `PLAN-ASSUMPTION-GATE`: `audit_ran` token valid; every HIGH resolved; no blanket accept (same predicate as SETUP-ASSUMPTION-GATE, plan-scoped). |
| 9 | **Build first unit** (S7) + STRICT green (G4) | "Refuse to pin without adversarial tests" — count can be 0 and still reported; adversarial tests **synthesized ≠ executed/green**; build may be a **cache/pin hit over 0 functions** so STRICT gates are "green" over nothing; a named STRICT gate can be missing and skipped (D3-style). Mutation "100%" over **0 mutants**. | `STRICT-GREEN`: from `build.result.json` assert `functions_built >= len(first_units)`; `pins[]` non-empty and each sha **recomputed==recorded**; the STRICT gate SET actually ran and each of {criteria, ack, stub-proof, change-proof, mutation-score, assumption} has `verdict=pass` **by name** (missing name = FAIL); `mutants_generated > 0` AND `mutation_score >= threshold`; `adversarial_tests_synthesized >= 1` AND each synthesized test id is **in the plan's test set** AND **passed** in the gate run (synthesized-and-green by test-id cross-check, not a raw count). Pin emission is **conditional in code** on the adversarial-green predicate. |
| 10 | **Review first build** (S8) — findings "fold upstream", **NO GATE** | rc 0 with unaddressed findings passes; "adversarial-verify each finding" is optional in prose; "fold upstream + rebuild" is a model action nothing proves happened; review may run 0 personas or the wrong ones. | **INSERT gate** `REVIEW-CLOSURE`: from `review.json` assert `personas_run ⊇` the SELECTION-FLOOR set (cross-check identical); `findings[]` present with each `adversarial_verified=true` (kill-plausible-but-wrong is mandatory); for every `verdict=real` finding there is a plan edit + **rebuild whose pin sha changed** referencing the finding id, and a re-review marks it resolved; **any open real finding → refuse**. Zero personas / no findings array → FAIL (D6). |
| 11 | **Wire-gates** (S9) + STANDING GREEN (G5) | **The headline hole.** wire-gates writes a `run_gates.py` whose `CHECKS` reference scripts that were never created; D3 makes them silently skip; G5 goes GREEN over **0 real checks**. Intake declared 3 data-quality gates; installing 0 passes. | wire-gates postcondition: for **every** declared gate (standing floor + each intake `data_quality_gate`) the script file exists, is importable/executable, AND is referenced in `CHECKS`; `wired == declared` (not `>=0`). `STANDING-GREEN`: run the (hardened, D3-fixed) `run_gates.py`; assert exit 0 AND `checks_run == checks_declared` AND `checks_declared >= floor{regression, stale_gate}` AND **each intake data_quality_gate name appears in the report as executed+pass**. |
| 12 | **Contract-installed meta-gate** (G6) | Proposed as a bare `bool`. A checkbox `contract_installed=true` is *itself* the ultimate vacuous gate — it asserts the very thing it's supposed to prove. | `CONTRACT-INSTALLED` must **observe the spine firing**, not read a flag: (a) the vendored routing table maps bare `do`/`build`/`review` → their contract (assert each mapping present in the entrypoint); (b) **red-team probe**: actually invoke `lathe do` with a sentinel in `projects/<name>` and assert a manifest was emitted (spine ran) **and** a deliberate contract-bypass attempt (raw build skipping the contract) is **REFUSED**; (c) prove the **manifest-finally** exists by running the probe with a **forced-fail work step** and asserting a (refuse) manifest still emits. Non-bypassability is demonstrated, not declared. |
| 13 | **Manifest** (S10) | D5 (crash before it) + a "render" that produces an empty-but-existing file + a manifest that *claims* `pass` while an artifact is missing + `rebuild_byte_identical:true` written without replaying (D1). | Emit via dispatcher **finally** (D5). Post-emit **schema validator**: manifest.json exists at the reserved path, parses, every base-spine field present+typed; `len(contributors) == steps_attempted`; `gates[]` has an entry per gate reached; if `verdict=="pass"` then **every hard gate = pass AND every guaranteed-artifact path exists** (config, pins, run_gates, NOTICE/CREDITS) — else the validator **downgrades to refuse** (the manifest cannot lie). `rebuild_byte_identical` may be `true` **only** with an attached `replay_evidence_hash` from an actual pin-replay that hit 0 live endpoints; otherwise it must be `null` (unverified), never a bare `true`. |

---

## Part 2 — HARDENED workflow (drop-in `workflows.py` steps)

Format `(kind, label, action)`. Inserted gates in **UPPERCASE**. Manifest is no longer a step (structural finally). Gates are hard unless noted.

```python
"onboard-project": {
  "desc": "Intake a new project, install the operating-contract spine, land a verified first "
          "build, wire + PROVE standing gates, and emit the onboard manifest (always, even on refuse).",
  "steps": [
    # [0 INTAKE] code — non-model
    ("auto", "intake: mint run_id; RESERVE manifest path; normalize+resolve <name> and target_dir", "intake new-project {name}"),
    ("gate", "TARGET-GUARD: name grammar; target strictly under projects/; absent-or-empty; git-clean; no project/config collision — all sub-checks pass, unknown=FAIL", ""),

    # [1 FRONT-END] skill+model, gated (WRITES config/behavior => mandatory)
    ("auto", "PROJECT-INTAKE INTERVIEW (requirements-liaison) -> CLARIFIED_SETUP.json + audit_ran token", "clarify --intake new-project {name}"),
    ("gate", "INTAKE-COMPLETENESS: every required field present/typed/non-empty; endpoints source!=default & not on public denylist unless posture authorizes; questions>=MIN; audit_ran valid", ""),
    ("auto", "SETUP ASSUMPTION AUDIT (assumption-auditor) -> CLARIFIED_SETUP.decisions.json + audit_ran token", "assume --setup {name}"),
    ("gate", "SETUP-ASSUMPTION-GATE: audit_ran valid; 4 required-risk postures each addressed; every HIGH resolved with distinct non-empty rationale (no blanket accept)", ""),

    # [2 SELECTION] code + catalog
    ("auto", "Decider selects personas/lenses for onboard -> selection.json (per-pick why+license+source)", "agent --for onboard {name}"),
    ("gate", "SELECTION-FLOOR: correctness+adversarial by name; security-reviewer iff intake flags auth/PII; every pick license_ok (fail-closed) & grounded non-empty why; unlicensed absent; set non-empty", ""),

    # [3 WORK]
    ("auto", "Scaffold dirs; vendor PINNED Lathe (content-hash); write lathe.config.json from CLARIFIED_SETUP; seed NOTICE/CREDITS", "scaffold {name}"),
    ("gate", "SCAFFOLD-POSTCOND: dirs present; config parses & endpoints byte-equal intake & no {placeholders}; vendored sha recomputed==recorded; NOTICE/CREDITS non-empty; stale_gate RUN (missing script=FAIL)", ""),
    ("auto", "SELFTEST live-probe of CONFIGURED endpoints -> selftest.json (model_echo + per-capability pass)", "selftest"),
    ("gate", "SELFTEST-PASS: both endpoints live round-trip echo configured model_id; 503->bounded-retry-then-FAIL; every REQUIRED capability pass; result well-formed", ""),
    ("you",  "Analyst authors first plan(s) for intake.first_units — small, PURE, >=4 asserts, declared KINDS", ""),
    ("gate", "FIRST-PLAN-VALID: plan(s) exist & import; CRITERIA + >=4 asserts + declared KINDS; pure; target fns == intake.first_units", ""),
    ("auto", "FIRST-PLAN ASSUMPTION AUDIT -> {plan}.decisions.json + audit_ran token", "assume {plan}"),
    ("gate", "PLAN-ASSUMPTION-GATE: audit_ran valid; every HIGH resolved; no blanket accept", ""),
    ("auto", "BUILD first unit under STRICT: best-of-N -> gate -> synthesize adversarial tests -> pin", "build {plan}"),
    ("gate", "STRICT-GREEN: functions_built>=first_units; pins recomputed-match; STRICT set {criteria,ack,stub-proof,change-proof,mutation-score,assumption} all pass BY NAME; mutants>0 & score>=thresh; adversarial tests synthesized>=1, in test set, GREEN; else refuse-pin", ""),

    # [4 ADVERSARIAL GATE]
    ("auto", "Review first build — floored personas -> review.json (personas_run, findings w/ adversarial_verified)", "review auto {files}"),
    ("gate", "REVIEW-CLOSURE: personas_run superset of selection set; every finding adversarial_verified; every REAL finding folded upstream + rebuilt (pin delta refs finding id) + resolved on re-review; no open real findings", ""),
    ("auto", "Wire standing + declared data-quality gates into qa/run_gates.py", "wire-gates {name}"),
    ("gate", "STANDING-GREEN: run_gates exit0 AND checks_run==checks_declared AND declared>=floor AND each intake data_quality_gate executed+pass (missing script=FAIL; 0 checks=FAIL)", ""),
    ("gate", "CONTRACT-INSTALLED (meta): routing maps bare do/build/review->contract; PROBE invocation emits a manifest & a bypass attempt is REFUSED; forced-fail probe still emits (manifest-finally proven)", ""),

    # [5 MANIFEST] — NOT a step: emitted by the dispatcher finally (always, even on refuse),
    #               then run through the post-emit schema validator that can DOWNGRADE pass->refuse.
  ],
}
```

**Dispatcher-enforced refuse guards (not in the skill):** first hard-gate fail → `verdict=refuse`, skip remaining WORK steps, flush partial manifest. Refuse to finish if either endpoint isn't live-echo reachable; to scaffold over a non-empty/dirty/out-of-tree target; to pin without synthesized-AND-green adversarial tests; to declare done unless STANDING-GREEN passes with `checks_run==checks_declared` AND CONTRACT-INSTALLED's probe fires; if any auto-used persona/model fails `license_ok`. Every refuse path still emits the (partial) manifest.

---

## Part 3 — HARDENED manifest fields (delta over the proposal)

Emitted by the **dispatcher finally**; validated post-emit. Additions in **bold**; changed types called out.

**Base (every invocation) — additions:**
```
emitted_by                   "dispatcher_finally"            # proves D5 fix
steps_attempted              int
steps_passed                 int
contributors                 [...]   # invariant: len(contributors) == steps_attempted
postconditions               [ {step_id, predicate_id, ok: bool, evidence_hash} ]   # D1/D2
front_end.clarify            { questions[], answers[], artifact_path,
                               fields: [ {key, value, SOURCE: "user"|"default", trace_answer_id} ],  # D-endpoint
                               audit_ran_token }                                     # D6
front_end.assumptions        { ledger[ {item, materiality, resolution, rationale, actor, ts} ],
                               required_risk_postures: [ {name, addressed: bool} ],  # the 4-item checklist
                               blanket_accept_detected: bool, audit_ran_token }
selection.personas[]         + LICENSE_OK: bool, FLOOR_MEMBER: bool, source, fetched, why_signal
gates[]                      + HARD: bool, PREDICATE_ID, evidence (non-empty when pass)
verdict                      "pass"|"refuse"
VERDICT_DOWNGRADED           bool         # validator flipped pass->refuse
downgrade_reason             string|null  # e.g. "verdict=pass but pins[] empty"
schema_valid                 bool
```

**Onboard-specific block — changes:**
```
scaffold.vendored_lathe      { version, sha, SHA_RECOMPUTED_MATCH: bool }            # #5
endpoints.analyst/impl       + MODEL_ECHO_MATCH: bool, retries_used, retry_capped: bool  # #6
selftest                     + required_capabilities: [ {name, present, pass} ]      # missing=fail
first_build                  { plans[], functions_built, first_units_expected,       # >= invariant
                               pins[ {fn, sha, RECOMPUTED_MATCH: bool} ],
                               strict: bool, STRICT_GATE_SET: [ {name, verdict} ],    # by-name, #9
                               MUTANTS_GENERATED: int, mutation_score: number,
                               ADVERSARIAL_TESTS: [ {id, IN_TEST_SET: bool, GREEN: bool} ] }
review                       { PERSONAS_RUN[], superset_of_selection: bool,          # #10
                               findings: [ {id, verdict, ADVERSARIAL_VERIFIED: bool,
                                            pin_sha_before, pin_sha_after, RESOLVED: bool} ],
                               open_real_findings: int }
standing_gates_wired         { CHECKS_DECLARED: int, CHECKS_RUN: int,                # #11 — equality asserted
                               floor_met: bool, gates: [ {gate, present, executed, verdict} ] }
data_quality_gates           [ {name, added: bool, executed: bool, verdict} ]         # executed, not just added
contract_installed           { routing_ok: bool, PROBE_MANIFEST_EMITTED: bool,        # #12 — object, not bool
                               BYPASS_REFUSED: bool, FINALLY_PRESENT: bool }
reproducibility              { rebuild_byte_identical: true|false|null,               # null unless replayed
                               REPLAY_EVIDENCE_HASH: string|null, model_calls_on_replay: int }
```

---

## Part 4 — Three code changes the implementer MUST land (holes live in shipped code, not just the workflow)

1. **`tools/flow_report.py::classify_step`** — stop scraping stdout. Add the postcondition-registry protocol (D1/D2): pass iff `rc==0 AND POSTCONDITIONS[step_id](run_dir).ok`. Make `workflow_verdict` FAIL on a status list shorter than the step count (D4).
2. **`qa/run_gates.py`** — a declared-but-missing check script is a **FAIL** not `continue`; `checks_run==0` or `< floor` → **exit nonzero**; cross-check `CHECKS` against `REQUIRED_CHECKS` (D3). This one file's `continue` is what makes STANDING-GREEN forgeable.
3. **Dispatcher / flow-runner** — move manifest emission into a `finally` that flushes an incrementally-built object (D5); add the hard/soft gate typing + halt-on-first-hard-fail (D7); add the post-emit schema validator that can downgrade `pass→refuse` (#13). This is where "guaranteed = deterministic code" actually gets its teeth.

**Bottom line:** the proposal's *phase structure* is right, but its guarantees are narrated, not enforced — they rest on `rc==0` + stdout prose + skip-if-missing gates, all three of which pass vacuously. The hardening converts every "the auditor blocks / the gate is green / the contract is installed" claim into a structured artifact + a code predicate that fails closed, inserts the seven missing gates (after setup-assume, selection, first-plan, plan-assume, review, and the two you-output guards), and makes the manifest a non-bypassable finally with a validator that refuses to let the record lie.