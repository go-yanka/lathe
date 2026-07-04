I've grounded the critique in the actual code. Here is the adversarial teardown and the hardened spec.

---

# Adversarial critique — `sdlc-requirements` — every hole + the deterministic check that closes it

## A. The existing flow-runner semantics INVERT your guarantees (must be replaced, not reused)

The proposed spine says "OUTPUT is gated by code." But the only verdict/classify code that exists today — `tools/flow_report.py` — is **PASS-by-default** and will pass this workflow vacuously. Three fatal holes, all in code you plan to lean on:

**H1 — Empty output = PASS.** `classify_step` (`flow_report.py:4-18`) returns `'pass'` whenever `rc==0` and the output string contains none of `['not exist','could be read','traceback','fail ::','error:']`. A step that **produces nothing at all** (empty string) hits none of the signals → `pass`. Any AUTO/GATE step that silently no-ops is green.
- **Close it:** a step's verdict must be a **positive assertion over a produced artifact**, never the absence of failure substrings. Every step declares `produces: <path>` + a `postcheck(path)->[]|problems`; verdict = `pass` iff the artifact exists AND `postcheck` returns `[]`. Delete the substring scanner.

**H2 — Every judgment step is PASS.** `classify_step(kind='you', …)` returns `'todo'` (`:8`), and `workflow_verdict` (`:20-31`) returns `PASS` unless some status is literally `'blocked'` — `'todo'` counts as PASS. So clarify, assumption-resolution, RTM authoring, and **ratification** — all `[YOU]` — pass without executing.
- **Close it:** `workflow_verdict` must map `todo`/`missing`/`unknown` → **REFUSE**, and the dispatcher must require every YOU step to attach a machine artifact that its GATE postcheck consumes. A YOU step with no gated artifact is a design error the loader rejects at registration time (see H23).

**H3 — Substring refereeing is bypassable both ways.** A wrong-but-polite model output ("everything looks great") passes; a correct artifact containing the literal `error:` (e.g. an FR about error handling) falsely blocks.
- **Close it:** gates parse **structured artifacts** (`rtm.json`, `criteria.json`, `assumptions.json`), never prose.

## B. The RTM gate passes the empty/degenerate set (the headline vacuous-pass)

**H4 — Zero requirements is "traceable."** I traced `rtm_gaps` (`sdlc_rtm.py`): `rtm_gaps({})` and `rtm_gaps({'UC':[],'BR':[],'FR':[],'TS':[]})` both return `[]`. An author that emits **nothing** passes the RTM gate, and Phase-4a's guard ("gaps must be `[]`") is satisfied.
- **Close it — `rtm_floor(layers, mins)`:** refuse unless every layer is non-empty and counts meet a floor scaled by thinking level (casual `UC≥1,BR≥1,FR≥1,TS≥1`; medium `≥2` each; high `≥3`). Run it **before** `rtm_gaps` and fold its problems into the gate. `gate = rtm_floor(...) + rtm_gaps(...)`.

**H5 — The set need not be about the goal.** `rtm_gaps` only checks the internal graph. `{UC-1:"the system works", BR-1:"it works", FR-1:"works", TS-1:"passes"}` is fully traceable and passes. Nothing ties requirements to `CLARIFIED_GOAL.md` or to the resolved assumptions.
- **Close it — `goal_coverage_gaps(clarified, decisions, layers)`:** deterministic ledger. Every `success_criterion` parsed from `CLARIFIED_GOAL.md` and every resolved decision id from `<run>.decisions.md` must map to ≥1 requirement id via an explicit `covers:[...]` back-reference in the rtm item. Uncovered criterion/decision → gap → REFUSE. This is what makes the front-end load-bearing instead of advisory.

**H6 — Placeholder text passes id+text checks.** `valid_id` only requires non-empty strings. `text:"TBD"`, `text:"x"` pass.
- **Close it — `content_floor(layers)`:** reject text matching a placeholder set (`tbd|tba|n/a|todo|fixme|xxx|...`, case-insensitive), reject `len(text.split())<4`, reject text equal (normalized) to the raw goal or to a parent's text (degenerate echo). Add to the gate.

## C. Front-end is placeholder-satisfiable

**H7 — Clarity gate (1b) checks emptiness only.** "success_criteria non-empty" passes on `"TBD"`, `"N/A"`, or the goal echoed verbatim.
- **Close it — `clarity_gaps(clarified_json)`:** require ≥1 measurable success criterion (contains a comparator/observable token: number, `must|shall|within|<=|>=|returns|rejects`), ≥1 explicit non-goal, none placeholder, none equal to the raw goal. Parse `CLARIFIED_GOAL.md` into a **required-field JSON** — "file exists" is not the check; "fields parse and pass" is.

**H8 — Assumption pre-audit passes on an empty ledger.** If the auditor returns `[]` (lazy call, timeout swallowed, or genuine miss), `blocking_unresolved==0` trivially holds and the run advances with nothing surfaced. Fail-closed on materiality only helps *if items exist*.
- **Close it — audit-ran proof + non-triviality floor:** the auditor call must return a receipt (`model, tokens, examined_dimensions:[inputs,outputs,state,failure,security,concurrency,...]`). `assumption_gaps`: REFUSE if the receipt is absent (call didn't happen) OR if the ledger is empty while the goal is non-trivial (`>N tokens`) — an empty ledger on a real goal is treated as **audit-not-run**, not "clean." Each item must carry `materiality∈{HIGH,MED,LOW}` (unknown→HIGH, already correct in `assumption_logic.blocking_assumptions`), and each HIGH must have a resolution whose `decision` text is non-placeholder AND names the rtm id it became (ties to H5). Reuse `unconfirmed_blockers(assumptions, confirmed, policy)` — its output must be `[]`.

## D. Selection (Phase 2) can fire ZERO personas and still "pass"

**H9 — `auto_spawn_for_goal` swallows all errors and returns `[]`.** `persona_spawn.py:129-132` — any exception (catalog missing, network down, curl timeout via `gh_json`) returns `[]` to stderr. The design's claim "CE floor guarantees `correctness-reviewer`" is **not in this code** — the floor is asserted nowhere. A degraded market → no lenses → workflow proceeds with no domain coverage, and requirement *completeness* (the whole point of Phase 2) silently evaporates.
- **Close it — offline CE floor, independent of the market.** Load the fixed floor (`correctness-reviewer`, plus the fixed front-end pair) directly from `ce_personas/` on disk — never through `auto_spawn`/GitHub. If a floor persona file is missing → REFUSE (`selection.ce_floor_loaded:false`). Record `market_status: live|degraded` and forbid PASS when a **required** lens failed to load.

**H10 — No deterministic goal→required-lens binding.** Design says "auth goal → security-reviewer" but `score_match` (`agent_router.py`) is fuzzy token overlap. "SSO login" or "credential rotation" may not tokenize to `security` → the whole authz/audit FR class is never demanded. Coverage of a domain is left to a fuzzy scorer.
- **Close it — `required_lenses(goal)` table (deterministic).** Keyed on canonicalized goal tokens (reuse `expand_words`): `auth|login|sso|oauth|credential|authz|authn → security-reviewer`; `migrate|migration|backfill → data-migration-reviewer`; `pii|data|record|ledger|persist → data-integrity-guardian`; `api|endpoint|contract → api-contract-reviewer`. If a trigger token is present and the mapped lens did **not** fire → REFUSE. Fuzzy selection may ADD lenses; it may never satisfy a required one.

## E. Adversarial gate (4b) self-refereed → zero-challenge vacuous pass

**H11 — "No findings" passes the gate.** Three adversaries that each return "looks fine" satisfy "each finding addressed/waived" vacuously — there are no findings. This is the model grading its own homework.
- **Close it — mandatory structured challenges + coverage evidence.** Each adversary must return ≥1 challenge `{target_id, class, description}` **or** a coverage receipt proving it examined every id in its scope (its challenge object must reference every UC/FR/TS id it considered; a null examination = gate-not-run = REFUSE). A zero-finding return without a full coverage receipt is REFUSE.

**H12 — "addressed" is unverifiable.** A challenge can be flipped to `addressed` with no change to the requirement set.
- **Close it — before/after digest.** Record `rtm_digest` before and after each adversarial round (`spec_digest`-style sha256 of canonical `rtm.json`). `addressed` REQUIRES `rtm_digest_after != rtm_digest_before` (the set actually changed) **or** an explicit `waived` with `{owner, reason}` (non-empty, recorded in manifest and counted). Deterministic: `verdict=='addressed' and digest_unchanged → REFUSE`.

**H13 — Testability gate is authored, not enforced.** The CRITERIA block ("each TS → falsifiable criterion → test_kind + suggested tests") is model-written with no check. `{ts_id:'TS-1', criterion:'works correctly', test_kind:'unit', suggested_tests:[]}` passes.
- **Close it — `testability_gaps(TS, criteria)`:** enforce 1:1 by `ts_id` (`set(ts_ids)==set(criteria.ts_id)`, both directions — no TS without a criterion, no orphan criterion), `test_kind ∈ {property,edge,unit}`, `suggested_tests` non-empty, `criterion` contains an observable/comparator token (else "not falsifiable"), and no placeholder text (reuse H6 set). `len(criteria)==len(TS)` exactly.

## F. Ratify + manifest — the "always-on" instrument that isn't guaranteed

**H14 — Ratify is a self-attestation.** "analyst ratification call must assert zero unresolved blocking" — the asserter is the thing being checked. Rubber stamp.
- **Close it — ratify is COMPUTED, not asserted.** `ratified` is a deterministic AND of machine facts, set by the dispatcher, unsettable by any skill:
  `ratified = clarity_gaps==[] ∧ unconfirmed_blockers==[] ∧ rtm_floor==[] ∧ rtm_gaps==[] ∧ goal_coverage_gaps==[] ∧ testability_gaps==[] ∧ required_lenses_all_fired ∧ every_adversarial_finding∈{addressed,waived} ∧ ce_floor_loaded`. The analyst produces evidence; code computes the verdict.

**H15 — Manifest not guaranteed on crash.** "always emitted" is a wish unless a code path guarantees it under exception/timeout/signal. A model-call throw in Phase 3 aborts before any manifest write.
- **Close it — open-first + finally-flush.** Phase 0 creates `docs/ce/<run>/` and writes the skeleton with `outcome:"refuse"`, `last_phase:"intake"` pre-populated. The dispatcher wraps the whole spine in `try/finally` (+ `atexit` + SIGTERM handler) that flushes the manifest. Each phase writes its slice incrementally and updates `last_phase`, so a crash leaves a **valid partial manifest** recording where and why it died.

**H16 — Incomplete manifest can be emitted.** Nothing validates the manifest has all fields. A refuse could omit `accounting`/`gates`.
- **Close it — `manifest_schema_gate(manifest)`.** Deterministic validator: every required key present, correct type, non-null **on refuse too** (a refusal must still record the phases that did run). The dispatcher exits non-zero and re-flushes if the manifest fails its own schema. The manifest validates itself before the process may exit.

**H17 — Accounting can be silently zero.** `cost_usd:0`, `tokens:0` is ambiguous ("free" vs "not recorded").
- **Close it:** each model call returns a usage receipt; any phase that made a call must have `tokens.total>0` OR an explicit `usage_unavailable:true, reason:"…"`. Never a silent 0.

## G. Control-flow & path holes

**H18 — Phase-4a loop-back is unbounded / can silently give up.** "loop back to Phase 3 with the gap list" — no bound; a stuck author loops forever or a caught exception downgrades to pass.
- **Close it:** bounded by `LATHE_TRIES`; on exhaustion → REFUSE with residual gaps in `gates.rtm_gate.gaps`. Never a downgraded pass. Same bound on 4b.

**H19 — Thinking-level "casual" can zero the pipeline.** The scaling table lets casual set interviewers→1 but nothing forbids a misconfig of interviewers=0, k=0, adversaries=0.
- **Close it — hard floors regardless of level:** `interviewers≥1`, `k≥1` (required-lens-inclusive), `adversaries≥1` (testability always among them), ratify always computed, manifest always emitted. Level raises ceilings; it can never drop below the floor. Enforce in a `resolve_dials(level)` that clamps.

**H20 — No requirements pin → downstream hand-edit undetectable.** The full `sdlc` workflow (`workflows.py:67`) consumes `REQUIREMENTS.md`/`rtm.json`. Nothing stops a human editing them post-ratify, violating "never hand-edit; fix the spec and regenerate."
- **Close it — `requirements_pin`.** Content-hash `rtm.json` (canonical) into the manifest and into a `REQUIREMENTS.md` header line. A `requirements_pin_gate` at the start of the downstream build recomputes and REFUSES on mismatch.

**H21 — Filenames derived from goal text = path injection / write failure.** `CLARIFIED_GOAL.md`, `<goal>.decisions.md` — a goal with `/`, `..`, or unicode breaks the write or escapes the dir; a crash here skips the manifest.
- **Close it:** all run artifacts live under `docs/ce/<run_id>/`; filenames derive from `run_id`, never raw goal. `run_id = ts + goal_digest[:8] + pid`; REFUSE to overwrite an existing manifest path (collision guard).

**H22 — Intake refuse-path must still emit.** Empty-goal guard says "refuse but emit manifest" — but if the skeleton is opened *after* the guard, the refuse emits nothing.
- **Close it:** skeleton open is the **first** action of Phase 0, before the goal-nonempty check; the empty-goal refuse just sets `outcome:refuse, refusal_reason:"empty goal"` on the already-open skeleton.

**H23 — A skill could omit a required gate from its step list.** The spine is only non-bypassable if the loader forbids a workflow definition that lacks the mandatory gates.
- **Close it — `validate_workflow_shape(defn)` at registration.** The `sdlc-requirements` contract declares a **required gate set** `{clarity, assumption, rtm_floor, rtm, goal_coverage, testability, adversarial, manifest_schema}`; the loader refuses to register / run any definition missing one, and refuses any YOU step without a `produces` + gated `postcheck`. This is the "skill can never disable the spine" enforcement, in code.

---

# Hardened workflow — implementer's spec

Typed steps (`AUTO`=deterministic dispatcher code, `GATE`=standing deterministic check, `YOU`=analyst call whose OUTPUT is gated). Every YOU step names the artifact it must produce and the GATE that consumes it. **PASS is never the default** — the verdict is a computed AND of gate results.

| # | Phase | Kind | Action | Produces | Deterministic guard (new function → file) |
|---|---|---|---|---|---|
| 0 | Intake | AUTO | mint `run_id=ts+digest[:8]+pid`, mkdir `docs/ce/<run_id>/`, **write skeleton `outcome:refuse` FIRST**, snapshot strict/version/level, clamp dials | `manifest.json` skeleton | `resolve_dials(level)` clamps floors (H19); empty goal → set refuse, emit, exit (H22); collision guard refuses overwrite (H21) |
| 1a | Clarify | YOU | `requirements-liaison` interrogates I/O/success/constraints/edge/non-goals | `CLARIFIED_GOAL.md` + `clarified.json` | — |
| 1b | Clarity gate | GATE | — | — | `clarity_gaps(clarified.json)==[]` (H7) → `sdlc_rtm.py` sibling |
| 1c | Assumption pre-audit | AUTO→YOU | `assumption-auditor` emits ledger; each HIGH resolved | `assumptions.json` + `<run>.decisions.md` | audit-ran receipt present + non-trivial-goal floor (H8); `unconfirmed_blockers(...)==[]`; each decision names an rtm id (H5) |
| 2 | Selection | AUTO | offline CE floor + `auto_spawn_for_goal` + required-lens table | `selection` slice | `ce_floor_loaded` (H9); `required_lenses(goal)` all fired (H10); record every considered persona |
| 3 | Author RTM + CRITERIA | YOU | author UC→BR→FR→TS `{id,text,traces_to,covers}` + criteria per TS, domain lenses injected | `rtm.json` + `criteria.json` + draft `REQUIREMENTS.md` | consumed by 4a/4b |
| 4a | RTM gate | GATE | — | — | `rtm_floor + rtm_gaps + content_floor + goal_coverage_gaps == []` (H4,H5,H6). Gaps → **do NOT write `REQUIREMENTS.md`**, loop to 3, bounded by `LATHE_TRIES` (H18) |
| 4b | Adversarial + testability gate | GATE | 3 adversaries generate cases; code enforces resolution | `challenges.json` | ≥1 structured challenge or full coverage receipt per adversary (H11); `addressed ⇒ rtm_digest changed` else `waived{owner,reason}` (H12); `testability_gaps==[]` (H13); bounded retries |
| 5 | Ratify | AUTO | `ratified` **computed** by dispatcher | set `ratified` | AND of all gate facts (H14); no self-attestation |
| 6 | Manifest | AUTO (finally) | render + `flow_report.render_report` twin | `manifest.json` + human render | `manifest_schema_gate(manifest)==[]` (H16); accounting non-silent (H17); always emitted via try/finally+atexit+signal (H15) |

**On PASS:** `REQUIREMENTS.md` (ratified, pinned header — H20), `rtm.json`, `criteria.json`, manifest + render.
**On REFUSE:** no `REQUIREMENTS.md`; manifest + render still emitted with `outcome:refuse`, `last_phase`, `refusal_reason`.

## New deterministic functions to build (all pure, gated, no I/O in the check)
- `rtm_floor(layers, mins) -> [problems]` (H4)
- `content_floor(layers, goal_text) -> [problems]` (H6)
- `goal_coverage_gaps(clarified, decisions, layers) -> [problems]` (H5)
- `clarity_gaps(clarified_json) -> [problems]` (H7)
- `assumption_gaps(ledger, receipt, goal_text, policy) -> [problems]` (H8) — wraps existing `unconfirmed_blockers`
- `required_lenses(goal_text) -> set[name]` + `selection_gaps(required, fired, floor_loaded) -> [problems]` (H9,H10)
- `testability_gaps(TS, criteria) -> [problems]` (H13)
- `adversarial_gaps(challenges, rtm_digest_before, rtm_digest_after) -> [problems]` (H11,H12)
- `compute_ratified(gate_facts) -> bool` (H14)
- `manifest_schema_gate(manifest) -> [problems]` (H16)
- `validate_workflow_shape(defn) -> [problems]` (H23) — run at load time
- **Replace** `classify_step`/`workflow_verdict` semantics: `todo`/`missing` → REFUSE, verdict = AND over gate postchecks, not absence-of-substring (H1,H2,H3)

## Hardened manifest schema (`docs/ce/<run_id>/manifest.json`) — every field populated on PASS **and** REFUSE

```
run_id, invocation:"sdlc-requirements", cli, lathe_version, strict:bool,
last_phase, outcome:"pass|refuse", refusal_reason|null,
intake:     { goal_raw, goal_digest, thinking_level, dials:{interviewers,k,assumption_scrutiny,tries,adversaries},
              ts_start, ts_end }
front_end:  { clarify:{ interviewers:[name], questions_asked:[..], answers:[..],
                        clarified_path, clarity_gate:{verdict, gaps:[..]} },   # gaps=[] required
              assumptions:{ audit_receipt:{model,tokens,examined_dimensions:[..]},   # absent ⇒ REFUSE
                            ledger:[{id,text,materiality,resolution,decision,became_rtm_id}],
                            blocking_unresolved:int(==0 to pass), decisions_path } }
selection:  { market_status:"live|degraded", ce_floor:[name], ce_floor_loaded:bool,
              required_lenses:[name], required_fired:bool,
              personas_considered:[{name,bucket,match_score,grade,picked,reason,explore_injected}],
              personas_fired:[name] }
work:       { layer_counts:{UC,BR,FR,TS}, floor_mins:{UC,BR,FR,TS}, rtm_path, rtm_digest, requirements_path,
              criteria_block:[{ts_id,criterion,suggested_tests:[..],test_kind}],   # len==|TS|
              coverage_ledger:[{criterion_or_decision_id, covered_by:[rtm_id]}],   # no empties to pass
              contributors:[{persona,layers_touched:[..],what_it_added_or_flagged}] }
gates:      { clarity:{verdict,gaps:[..]}, assumption:{verdict,unresolved:[..]},
              rtm_floor:{verdict,gaps:[..]}, rtm:{verdict,gaps:[..]}, content:{verdict,gaps:[..]},
              goal_coverage:{verdict,gaps:[..]}, testability:{verdict,untestable_ts:[..]},
              adversarial:[{adversary,challenge:{target_id,class,description},
                            verdict:"addressed|waived", rtm_digest_before, rtm_digest_after, resolution, waiver:{owner,reason}|null}],
              retries:{rtm:int, adversarial:int, tries_max:int},
              gate_overall:"PASS|REFUSE" }
ratify:     { ratified:bool(computed), computed_from:[gate names], refusal_reason|null }
accounting: { models:{analyst_model,...}, tokens:{prompt,completion,total},   # >0 or usage_unavailable
              usage_unavailable:bool, cost_usd, timing_ms:{per_phase:{...}, total},
              requirements_pin:sha256|null }
```

`manifest_schema_gate` enforces presence + type + non-null-on-refuse for every key above; the dispatcher cannot exit until it returns `[]`.

## Load-bearing files the implementer touches
- Replace verdict semantics: `/home/user/lathe/projects/agentic-harness/tools/flow_report.py` (H1-H3)
- Extend RTM gate: `/home/user/lathe/projects/agentic-harness/tools/sdlc_rtm.py` + spec in `/home/user/lathe/projects/agentic-harness/plans/H_sdlc.py` (H4-H6)
- Reuse assumption gate: `/home/user/lathe/projects/agentic-harness/tools/assumption_logic.py` (`unconfirmed_blockers`, `spec_digest` for rtm_digest) (H8,H12)
- Harden selection (do NOT trust the silent `[]`): `/home/user/lathe/projects/agentic-harness/tools/persona_spawn.py:129`, decider `/home/user/lathe/projects/agentic-harness/tools/agent_router.py` (`expand_words` for the required-lens table) (H9,H10)
- Register + shape-validate + wire the spine and manifest finally-flush: `/home/user/lathe/projects/agentic-harness/tools/workflows.py` (`sdlc` entry, `:67`) and dispatcher `/home/user/lathe/projects/agentic-harness/tools/dispatcher.py` (H15,H22,H23)

**Bottom line:** as proposed, the workflow passes on an empty requirement set (H4), a goal-unrelated set (H5), a placeholder clarify (H7), an empty assumption ledger (H8), zero personas (H9), zero adversarial findings (H11), and — because of the existing `flow_report` verdict semantics — every judgment step and any silent no-op step (H1,H2). The nine new pure gates plus the computed-ratify and finally-flushed self-validating manifest convert each of those vacuous passes into a recorded REFUSE.