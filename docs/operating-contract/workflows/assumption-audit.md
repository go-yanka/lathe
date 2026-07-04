I've read the real machinery: `cmd_assume` (`lathe.py:1210-1378`), the pure logic (`assumption_logic.py` / `H_assumption_logic.py`), `request_spec.py`, `W01_flow_report.py`, the `assumption-auditor` persona, and `OPERATING_CONTRACT_DESIGN.md`. Here is the adversarial critique and hardened spec.

---

# ADVERSARIAL CRITIQUE — `lathe assume` (invocation: assumption-audit)

The proposed design is well-mapped to the code, but it inherits the current implementation's central weakness: **a failed/empty audit is byte-indistinguishable from a clean audit, and both return `0`.** Most "guards" in the design are gated behind the `--think` dial, which means the caller can turn off the enforcement that matters most. Below, every hole is grounded in a specific line, with the deterministic check that closes it.

## The root defect (enables holes 1, 2, 9, 13, 15)
`request_spec` returns `""` on an unreachable/errored analyst (real code, `request_spec.py`, final `return ""`). In `cmd_assume:1358-1359`:
```
raw = request_spec(...) or ""
ledger = [] if "no assumptions" in raw.lower()[:40] else parse_assumptions(raw)
```
`parse_assumptions("")` → `[]` → zero blockers → `return 0`. **A dead endpoint produces "0 assumptions, build unblocked."** The design's self-collapse guard fires only at `high` thinking and only *downgrades to advisory* while still returning `0`, so at `casual`/`medium` a stubbed analyst is a silent PASS that the build's `LATHE_ASSUMPTION_GATE` reads as clean.

**Core fix — a three-state audit outcome, computed in code, unconditional at every thinking level:**
- `AUDITED_NONEMPTY` — response non-empty, ≥1 line parsed by `parse_assumptions`.
- `AUDITED_ZERO` — response's *entire stripped payload* equals the sentinel (`raw.strip().lower() == "no assumptions"`), corroborated by ≥2 independent auditor calls.
- `NO_AUDIT` — empty/whitespace/timeout/HTTP-error response, OR non-empty-but-parsed-to-zero-and-not-sentinel (parse failure).

Only the first two mean "the auditor ran." `NO_AUDIT` ⇒ `verdict=REFUSED`, `rc=3`, never a clean `0`. This requires making `request_spec` return a structured result (`{text, http_status, bytes, tokens_in, tokens_out}`) so the spine has *proof of work*, not a bare string it can't distinguish from silence.

---

## Enumerated holes

**H1 — Dead endpoint → vacuous clean audit.** (`:1358`) *Closed by* the three-state outcome above: empty response is `NO_AUDIT`/`REFUSED`, rc≠0. Manifest records `intake.analyst_reachable`, `contributors[].proof_of_work`.

**H2 — Forgeable / substring "NO ASSUMPTIONS".** (`:1359`) `"no assumptions" in raw.lower()[:40]` collapses the ledger on any first-40-char match ("No assumptions are trivial; here are the real ones…"), and a canned stub string passes. *Closed by:* accept a zero-ledger **only** when `raw.strip().lower() == "no assumptions"` (exact, whole payload) AND ≥2 independent auditors agree. Non-empty-but-parses-to-zero-and-not-sentinel ⇒ `PARSE_FAILURE` ⇒ gate fail (record `raw_lines>0, parsed==0`).

**H3 — Manifest NOT emitted on early-refusal paths.** Every early `return` (`:1243` rc2, `:1246` rc2, `:1252` rc1, `:1255` rc0, `:1274` rc2) exits before any record; there is currently **no manifest write at all**. *Closed by:* the spine mints the manifest path in Phase 0 and registers an `atexit`/`finally` flush seeded `verdict=REFUSED`, so any exit path (including uncaught exception / `KeyboardInterrupt`, which `:1320` already swallows in resolve) flushes a manifest. Post-condition: flow-runner asserts `exists(manifest_path)`; if absent, *it* writes a crash stub. Lives in the spine, not `cmd_assume` — non-bypassable.

**H4 — "no FUNCTIONS" returns rc0.** (`:1254-1255`) rc0 is the clean signal; an empty/broken plan certifies clean. *Closed by:* empty auditable surface ⇒ `REFUSED`, distinct `rc=3`, `intake.refused=true, refuse_reason="empty FUNCTIONS"`. The build gate must treat `REFUSED` as blocking, never passing.

**H5 — State persisted BEFORE the gate; non-atomic write.** (`:1363-1364`) The new ledger is written to `.assumptions.json` before any Phase-4 adversarial check, and via plain `open(...,"w")` — a torn write yields `data={}` on next read (`:1263`, silent) → empty state → unblocked. *Closed by:* (a) atomic `tmp`+`os.replace`; (b) persist only *after* the gate assigns a verdict; (c) store `schema_version` + `gate_verdict` in the entry; the build gate refuses any entry whose `gate_verdict != "AUDITED"` or is absent (a half-written/legacy entry is un-audited, not clean).

**H6 — `spec_digest` binds spec text only.** (`assumption_logic.py:120`) It hashes `name/prompt/tests` but not the **goal** (`plan.__doc__`, fed to the auditor at `:1354`), the **policy**, the **persona**, or the **model**. Changing the goal, or tightening policy `high→high+med`, keeps prior `confirmed` though newly-blocking items were never reviewed. *Closed by:* `audit_digest = sha256(spec_digest ⊕ goal ⊕ policy ⊕ persona_hash ⊕ auditor_model_id)`. Prior confirmations kept iff full `audit_digest` matches; else `digest_stale=true`, drop confirmations, re-open. Manifest records both digests + which component changed.

**H7 — Placeholder decisions clear high blockers vacuously.** (`:1329-1330`) The `stated intent` branch accepts *any* non-`s`/non-empty `raw` — `"x"`, `"."`, `"tbd"` — as a decision that unblocks a `high` item. In autonomous mode, the analyst's gated output can satisfy the gate with a token. *Closed by:* a **decision-substance gate** in code: `decision.strip()` non-empty, not solely punctuation, length ≥ floor, and for `stated intent` not equal to the echoed prompt/assumption text. A decision failing the check is rejected → item stays blocking. This directly closes "a placeholder that passes."

**H8 — `--accept-all` / `--answers` bulk vacuous clearance.** (`:1283-1299`) `--accept-all` clears every blocker and returns `0` with no cap, no actor, no per-item substance; an autonomous agent can route through it to defeat the whole gate. *Closed by:* (a) under `LATHE_STRICT`, **high-materiality items cannot be cleared by bulk** — only per-item, individually attributable; (b) `--accept-all` stamps `verdict=ADVISORY` (never PASS) + `bulk_accept=true, count, actor, reason`; the build gate under STRICT refuses bulk-cleared high items; (c) `--answers` decisions run through the H7 substance gate (a file of `"a"` lines does not mass-clear).

**H9 — The liveness & anti-rubber-stamp gates are dial-gated.** The design's own table makes self-collapse liveness (`high` only) and anti-rubber-stamp (`medium`+) conditional on `--think`. The check that most needs to be unconditional ("did the auditor actually work?") is behind a caller-controlled dial. *Closed by:* split **"did the work happen" (always enforced, it's a code property) from "how hard we pushed" (scales with thinking)**. Liveness/three-state outcome and anti-rubber-stamp run at every level; only co-auditor count and promotion synthesis scale. The dial never reaches zero enforcement.

**H10 — Anti-rubber-stamp trips on a model's own flag (circular).** The design fails the gate only if "a domain lens flagged" a risk category — but that lens is a model call that can vacuously collapse (H1), producing no flag → no trip. *Closed by:* derive the risk signal **deterministically** — keyword scan of `FUNCTIONS` names/prompts for `auth|token|password|delete|drop|migrat|encod|decrypt|pii|payment|charge|refund|order|idempoten|concurren|persist`. If a risk keyword is present AND the ledger has zero `high`/`med` items ⇒ `anti_rubber_stamp=FAIL`, regardless of any lens. Code owns the trip-wire; the model only adds detail.

**H11 — Merge dedup can drop a real `high`.** The design dedupes by normalized text (`unconfirmed_blockers`' lossy `re.sub(r"\s+"," ",lower.strip())`) and "takes max," but two distinct assumptions colliding on normalized text drop one — a real `high` can vanish. *Closed by:* dedup key = `(normalized_text, category)`; on collision keep max materiality AND union `sources`/`options`; **post-condition assert: the set of merged `high` texts ⊇ every auditor's `high` texts.** If any `high` would be dropped by collision, keep both (append disambiguator). Manifest logs `merge_dropped`. Fail-closed: when unsure two are the same, keep both.

**H12 — Zero co-auditors + disabled liveness at `casual`.** The design allows `casual=0` co-auditors, and (H9) disables liveness at `casual` — exactly the level where a lone possibly-stubbed auditor's empty ledger passes with no corroborator. "CE floor guaranteed" is prose. *Closed by:* spine asserts `"correctness-reviewer" in selection.effective_set` and `count(auditors returning parseable-or-sentinel) >= 1` before any clean verdict; a **zero-ledger requires ≥2 independent sentinel responses** at every level or verdict caps at `ADVISORY` (build gate treats ADVISORY as blocking under STRICT).

**H13 — Promotion synthesis (low→high) can be vacuously skipped.** At `high`, the "construct a failing scenario" pass is a model call; if it returns `""` it promotes nothing → the `low` passes, and "found nothing to promote" is indistinguishable from "endpoint dead." *Closed by:* the promotion call emits proof-of-work; `promotion_synthesis ∈ {ran_found_none, ran_promoted_k, UNAVAILABLE}`; `UNAVAILABLE` caps verdict at `ADVISORY` — cannot certify adversarial depth as PASS.

**H14 — Frozen policy is not authoritative at build time.** Audit freezes `policy` into the entry (`:1363`), but the build gate recomputes blockers with `LATHE_ASSUMPTION_POLICY` at *build* time. Audit at `high+med`, then build with `LATHE_ASSUMPTION_POLICY=off` → `unconfirmed_blockers` returns `[]` (see `off` branch in all three pure fns) → unblocked. *Closed by:* order policies `off < high < high+med < all`; the build gate uses `max(frozen, env)` (stricter wins) and **refuses on downgrade**: `resolve(env) < resolve(entry.policy)` ⇒ REFUSE "policy weakened since audit; re-run assume."

**H15 — Corrupt state silently resets.** (`:1261-1264`) Any read exception → `data={}` → prior blockers discarded. Corruption + dead endpoint = clean. *Closed by:* distinguish absent (ok, first run) from present-but-unparseable (`REFUSED`, rc≠0, "corrupt .assumptions.json"). Never silently reset a corrupt audit.

**H16 — Artifact writes unverified.** `_assume_write_decisions` (`:1196`) does bare `open(...,"w").write` with no check; a failed write leaves state "resolved" with no trail. *Closed by:* spine post-condition — after the subcommand, assert all three artifacts exist, are non-empty, and parse (manifest = valid JSON with required keys; decisions.md non-empty; entry has `gate_verdict`). Atomic writes + fsync before declaring success; any miss ⇒ flow-runner writes REFUSED manifest, returns nonzero.

**H17 — Manifest present but vacuous.** Nothing forbids `verdict=PASS` with `contributors=[]`, `models=[]`, `cost=null` — phase 5 "satisfied" while recording nothing. *Closed by:* a **manifest schema validator in the spine** (below). PASS is only stampable if the manifest validates non-vacuously. The manifest self-guards.

**H18 — thinking/model/cost self-reported by the skill.** A skill could claim `high` while doing `casual` work. *Closed by:* the dispatcher (not the skill) writes `thinking_level` (resolved in Phase 0) and `models`/`tokens` (from `request_spec` transport usage). Cross-check: `high` requires ≥2 auditor calls in `contributors`; a mismatch bars PASS-at-high.

**H19 — Goal-thinness only "downgrades confidence."** A one-line docstring makes the auditor hallucinate or emit nothing, yet returns `0`. *Closed by:* deterministic goal-substance floor (`len(goal.split()) >= N` and ≥1 input/output/behavior signal word). `goal_thin AND ledger empty` ⇒ verdict `ADVISORY`, not PASS. Code owns the test, not the liaison model.

**H20 — run_id / manifest-path collision.** Reusing `<plan>` basename overwrites a prior refusal record. *Closed by:* `run_id=uuid4`; create manifest with `O_EXCL`; collision → new id. Manifests immutable/append-only.

---

# HARDENED WORKFLOW

## Spine invariants (deterministic code, non-bypassable, thinking-independent)
1. **Manifest path minted at Phase 0, flushed on every exit** (atexit + post-condition assert). Default seed `verdict=REFUSED`.
2. **Three-state audit outcome** (`AUDITED_NONEMPTY | AUDITED_ZERO | NO_AUDIT`) computed from `request_spec` proof-of-work. `NO_AUDIT` never yields a clean `0`.
3. **Zero-ledger requires exact whole-payload sentinel + ≥2 independent corroborations.**
4. **State persisted only after the gate, atomically, with `gate_verdict` + `audit_digest`.**
5. **Policy monotonicity:** build gate uses `max(frozen, env)`; downgrade ⇒ REFUSE.
6. **rc contract:** `0`=PASS(clear), `1`=BLOCKED(blockers remain), `2`=usage/arg error, `3`=REFUSED(no audit / empty FUNCTIONS / corrupt state / analyst unreachable). The build gate treats `1` and `3` as blocking; only `0` proceeds.

## Phases (typed, with guards)

**P0 Intake `[AUTO]`** — mint `run_id`(uuid4)+manifest path(O_EXCL); load plan (fail⇒rc3 + manifest); `fns` empty ⇒ rc3 REFUSED (H4); read `.assumptions.json` distinguishing absent vs corrupt (H15); compute `spec_digest` and full `audit_digest` (H6); resolve `thinking_level` here, spine-owned (H18). Deterministic goal-substance test → `goal_thin` (H19); deterministic risk-keyword scan → `risk_categories` (H10).

**P1 Front-end `[YOU→AUTO, gated]`** — resolve scrutiny policy (flag>env>`high`), **freeze into run and manifest** as an ordered enum. Liaison advisory is recorded; `goal_thin` is enforced (caps verdict, H19), not merely noted.

**P2 Selection `[AUTO]`** — decider selects domain co-auditors by the *deterministic* `risk_categories` (not a model flag). Spine asserts `correctness-reviewer ∈ effective_set` (H12). Count scales with thinking; **enforcement does not** (H9). Selection + per-persona *why* is a required manifest field.

**P3 Work `[AUTO+AUTO+YOU]`** —
 (1) *Audit*: each auditor via `request_spec`; capture proof-of-work per call; classify each into the three-state outcome. `parse_assumptions` fail-closed (unranked→high) preserved.
 (2) *Merge & rank*: dedup key `(norm_text, category)`, max-materiality, union sources/options; **assert no `high` dropped** (H11). Compute `blocking_assumptions` → `unconfirmed_blockers` under frozen policy.
 (3) *Resolve* (`--resolve`): per-item decision through the **substance gate** (H7); `--answers` same gate (H8); `--accept-all` ⇒ ADVISORY + actor/reason, and under STRICT cannot clear `high` (H8).

**P4 Adversarial gate `[GATE]`** — all unconditional except depth:
 - `liveness`: `AUDITED_ZERO` requires ≥2 sentinel corroborations else ADVISORY (H1/H12) — **every level**.
 - `parse_integrity`: any auditor with `raw_lines>0, parsed==0`, not sentinel ⇒ FAIL (H2).
 - `anti_rubber_stamp`: deterministic risk keyword present + zero high/med ⇒ FAIL (H10) — **every level**.
 - `promotion_synthesis` (high only): proof-of-work required; `UNAVAILABLE`⇒cap ADVISORY (H13).
 - `blocker_clearance`: `unconfirmed_blockers(max(frozen,env)) == []` (H14). rc `0` iff clear.

**P5 Manifest `[AUTO]`** — always; validated by the schema validator before any PASS stamp (H17). Post-condition asserts all three artifacts exist/non-empty/parse (H16).

## Manifest schema validator (spine refuses to stamp PASS unless all hold)
- `verdict ∈ {PASS, BLOCKED, ADVISORY, REFUSED}`.
- `verdict==PASS` ⇒ `gate.blocker_clearance=="PASS"` AND `≥1` contributor with `proof_of_work==true` AND every `models[].model` non-empty AND `gate.liveness=="pass"` AND `gate.anti_rubber_stamp=="pass"` AND `gate.parse_integrity=="pass"`.
- `verdict==PASS` AND `thinking_level=="high"` ⇒ `count(contributors role=auditor) ≥ 2` AND `gate.promotion_synthesis != "UNAVAILABLE"`.
- `intake.refused==true` ⇒ `refuse_reason` non-empty AND `verdict=="REFUSED"`.
- `AUDITED_ZERO` accepted as clean ⇒ `gate.zero_corroborations ≥ 2`.
- `bulk_accept==true` ⇒ `verdict != "PASS"` (ADVISORY) unless every bulk item is `low` under a non-STRICT policy.

## Hardened manifest fields (`docs/ce/<run_id>.assume.manifest.json`)
```json
{
  "schema_version": 1, "run_id": "uuid4", "invocation": "assumption-audit",
  "cli": "lathe assume <plan> [--resolve]", "ts_start": "", "ts_end": "", "duration_ms": 0,
  "thinking_level": "medium",                                  // spine-owned (H18)
  "rc": 0,                                                      // 0/1/2/3 contract
  "intake": { "plan_path": "", "plan_key": "", "goal": "",
    "spec_digest": "", "audit_digest": "", "prior_audit_digest": "",  // (H6)
    "digest_stale": false, "digest_changed_component": null,
    "function_count": 0, "goal_thin": false,                   // (H19)
    "risk_categories": ["data","security"],                    // deterministic scan (H10)
    "analyst_reachable": true,                                 // (H1)
    "state_file": "present|absent|corrupt",                    // (H15)
    "refused": false, "refuse_reason": null },
  "front_end": { "scrutiny_policy": "high", "policy_source": "flag|env|config|default",
    "policy_rank": 1, "liaison_advisory": null, "scrutiny_recommendation": null },
  "selection": { "fixed": ["assumption-auditor"], "ce_floor_present": true,   // (H12)
    "co_auditors": [{"persona":"data-integrity","why":"risk_categories∋data","rating":7.2,"source":"vendored"}],
    "decider_pool_size": 0 },
  "contributors": [                                            // spine-measured, not self-reported
    {"persona":"assumption-auditor","role":"auditor","endpoint":"","http_status":200,
     "response_bytes":812,"raw_lines":11,"parsed":9,"outcome":"AUDITED_NONEMPTY",
     "proof_of_work":true,"tokens_in":0,"tokens_out":0}],
  "audit_outcome": "AUDITED_NONEMPTY|AUDITED_ZERO|NO_AUDIT",  // (H1/H2)
  "ledger": [{"materiality":"high","category":"data","text":"","options":[],
    "sources":["assumption-auditor","data-integrity"],"blocks":true,
    "status":"open|decided","decision":null,"via":null}],
  "merge": { "merged_total": 9, "merge_dropped": 0, "high_preserved_assert": "pass" }, // (H11)
  "counts": {"total":0,"high":0,"med":0,"low":0,"blocking":0,"unconfirmed_blockers":0},
  "decisions": [{"assumption":"","decision":"","via":"chose alternative",
    "materiality":"high","category":"data","substance_gate":"pass","actor":"analyst|user"}], // (H7/H8)
  "gate": { "liveness":"pass|advisory-downgrade", "zero_corroborations":0,     // (H1/H12)
    "parse_integrity":"pass|fail", "anti_rubber_stamp":"pass|fail",            // (H2/H10)
    "promotion_synthesis":"ran_found_none|ran_promoted_k|UNAVAILABLE|n/a",     // (H13)
    "promotions":[{"text":"","from":"low","to":"high","scenario":""}],
    "policy_at_build":"high","policy_monotonic":"pass|refuse-downgrade",       // (H14)
    "blocker_clearance":"PASS|BLOCKED", "unconfirmed_after":0 },
  "bulk_accept": {"used":false,"count":0,"actor":null,"reason":null},          // (H8)
  "models": [{"role":"auditor","model":"","endpoint":""}],                     // spine-measured
  "cost": {"tokens_in":0,"tokens_out":0,"usd":0.0},
  "verdict": "PASS|BLOCKED|ADVISORY|REFUSED",
  "manifest_valid": true,                                                      // (H17) validator result
  "artifacts": {"decisions_md":"<plan>.decisions.md","state_json":".assumptions.json",
    "manifest":"docs/ce/<run_id>.assume.manifest.json","artifacts_verified":true} // (H16)
}
```

## Verdict rule (reusing `W01_flow_report` semantics, hardened)
`workflow_verdict`/`classify_step` currently map `rc!=0 → blocked`, else scan output for failure signals — but `classify_step('auto',0,'')=='pass'`, which is exactly the vacuous-clean trap (`test :23`). So the assume gate must **not** feed a bare rc/output to `classify_step`; it feeds the *validated manifest*:
- `REFUSED` iff `intake.refused` or `audit_outcome==NO_AUDIT` or `state_file=="corrupt"` or policy downgrade.
- `BLOCKED` iff `gate.blocker_clearance=="BLOCKED"`.
- `ADVISORY` iff clear-but-uncertain: `goal_thin`, lone-sentinel zero-ledger, `promotion_synthesis==UNAVAILABLE`, or `bulk_accept` on non-STRICT.
- `PASS` iff `manifest_valid` and none of the above.

The single most important change: **`return 0` must require positive proof the auditor ran and the manifest validated — silence, emptiness, corruption, and downgrade all resolve to rc≠0**, so the build's `LATHE_ASSUMPTION_GATE` can never mistake "we couldn't audit" for "there's nothing to audit."

Key source anchors for the implementer: `lathe.py:1210-1378` (dispatch + both modes), `:1358-1359` (the collapse point), `:1363-1366` (pre-gate non-atomic persist), `assumption_logic.py:40-64,66-118,120-137` (policy/off branches the build gate must not weaken), `request_spec.py` (must return structured usage, not a bare string).