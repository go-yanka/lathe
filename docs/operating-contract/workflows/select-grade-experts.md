Adversarial critique complete. Grounding confirmed against the real code (`agent_router.py`, `persona_spawn.py`, `persona_ratings.py`, `persona_market.py`, `lathe.py` `cmd_agent` at 963–1097). Note up front: `agents/catalog.json`, `agents/ratings.json`, and `agents/usage.jsonl` **do not exist yet** — the reflexive tool's own inputs are missing, which is itself hole H2/H32 below.

---

# ADVERSARIAL CRITIQUE — `select-grade-experts`

## Legend
Each hole: **where** it lives → **how it skips/nulls/passes-vacuously** → **the deterministic check (code) that closes it**. Line refs are to current code.

---

## PHASE 0 — INTAKE

**H1 — Unknown/empty verb bypasses the entire spine.**
`cmd_agent` bare/unknown args fall through to `print(usage); return 2` (lathe.py:1092-1094) — no run_id, no manifest. The contract is routed *around*, not *through*.
→ **Check:** dispatcher classifies verb ∈ {find,rate,bucket,UNKNOWN} *before* any work; UNKNOWN still mints `run_id` and emits a `verdict:"refuse", refuse_reason:"unknown_verb"` manifest. Wrap the whole body so **every** return path (incl. 975, 1049, 1082, 1094) exits through the emitter.

**H2 — Catalog-unavailable returns bare `1` with no record.**
lathe.py:973-975 `return 1` on catalog load failure. The reflexive tool silently produces nothing when its own input is missing (currently the *default* state — file is MISSING).
→ **Check:** catalog load failure ⇒ refuse manifest `refuse_reason:"catalog_unavailable"`. Add catalog-integrity probe: non-empty list, every entry has a `name`; else refuse. Missing `ratings.json` ⇒ `{}` (fine); missing `usage.jsonl` ⇒ empty ledger with `ledger_absent:true` (NOT an error).

**H3 — `need_digest`/`ambiguous` not always computed.** For reproducibility the digest must exist even on bucket.
→ **Check:** emitter asserts `intake.need_digest` present for all verbs; `ambiguous` present for find/rate.

---

## PHASE 1 — FRONT-END

**H4 — "Skipped" is indistinguishable from "crashed."** `bucket→skipped`, `find→only if ambiguous`. An empty `clarify:[]` could mean *ran, nothing needed* OR *never ran*.
→ **Check:** require `frontend.status ∈ {ran, skipped_by_rule:<rule_id>, blocked}`; emitter refuses a manifest missing it.

**H5 — `rate` HIGH-block is vacuous in auto/no-TTY.** Spec says HIGH-materiality assumptions block, but with no interactive resolver an implementation will auto-approve defaults and mark them "decided." The only behavior-mutating verb then bakes in silent choices — the exact failure the audit exists to prevent.
→ **Check:** for verb=rate, `assumption_gate` reads `.decisions.md`; any assumption with `materiality:"HIGH"` whose `resolution ∉ {decided:*}` ⇒ `verdict:"refuse"`, and assert `ratings_after_digest == ratings_before_digest` (no write happened). **Auto-mode may NOT downgrade a HIGH assumption to a recorded-assumption to unblock itself.**

**H6 — Two of the four "assumptions" are actually invariants being laundered as decidable.** Judge-identity (#3) and write-semantics/no-overwrite (#2) must not be "decided away" as assumptions — an implementer could mark them `decided:default` and pass.
→ **Fix (design):** move #2 and #3 out of front-end into **hard Phase-4 gates** (grade-integrity, judge-independence). Front-end only surfaces the genuinely tunable knobs: `N_min` and `recency_window`.

---

## PHASE 2 — SELECTION (anti-bootstrap)

**H7 — The anti-bootstrap rule is prose, not enforced.** Nothing stops a future edit from wiring `load_ratings()` into meta-lens selection, reintroducing the loop.
→ **Check:** the Phase-2 selection function signature for this invocation takes **only `(verb, thinking_level)`** — no ledger/ratings params in scope. Add a regression test: run selection with a **poisoned `ratings.json`** and assert the meta-lens set is byte-identical (proves grades don't influence staffing). `meta_lenses` is a frozen literal; determinism asserts equality to that constant.

**H8 — `fired:[]` passes vacuously.**
→ **Check:** verb→required-lens map (find⇒selection-strategist, rate⇒assessment-auditor, bucket⇒taxonomist); emitter asserts the required lens ∈ `fired`, else refuse.

---

## PHASE 3 — WORK / `find`

**H9 — `select_agents_for_goal` returns `[]` (agent_router.py:59-76) → `find` "succeeds" producing nothing.** Only returns score>0 personas; empty on no-overlap or exception. `chosen:[]` could still verdict `pass`.
→ **Check (productivity gate, see H24):** find with a need yielding ≥1 canonical token MUST return ≥1 candidate OR `verdict:"refuse", refuse_reason:"no_match"`. A `pass` with empty `chosen` is auto-converted to refuse.

**H10 — Cold-start prior can dominate / grade-gaming.** `apply_ratings` (persona_ratings.py:38-42) multiplies score by `0.5 + rating/10`: an **unrated** persona keeps full weight (1.0×) while a proven-bad (rating 0) persona is penalized to 0.5×. So *never being rated outranks being rated badly* — starving personas flood the exploit head, and there's an incentive never to be measured.
→ **Check:** cold-start prior is a **fixed constant strictly below the median earned grade**, and cold-start personas may enter **only via the explore slot**, never the exploit head. Gate asserts every persona with `source:"exploit"` has `sample_size ≥ 1`.

**H11 — Explore silently no-fires → starvation "silently skipped" (the gate's own stated enemy).** Explore draws "from matching buckets"; if no eligible unused persona exists, or ε roll fails, nothing fires and nothing records why. Current code has **no explore at all**.
→ **Check:** record `epsilon`, RNG `seed`, and the actual `roll` value. `explore_fired` gate = `(thinking_level != casual AND coverage < threshold)` ⇒ (`explore` slot fired) OR (`explore_skipped_reason ∈ {no_eligible_tail, epsilon_roll_below}`). **Empty/absent reason ⇒ refuse.** Seed+roll recorded so determinism can replay it.

**H12 — Determinism gate is unsatisfiable OR vacuous because the ledger mutates every run.** Spec §4 appends a line to `usage.jsonl` every run; rerunning "same ledger" is impossible against the live file.
→ **Check:** determinism is defined over a **pinned ledger snapshot digest** (`ledger.snapshot_digest`) captured at intake; the gate replays selection against that exact digest, not the live file. The self-append (H30) happens **after** the snapshot.

**H13 — Mandatory persona silently dropped.** `apply_overrides` filters `[m for m in mand if m in _names]` (persona_spawn.py:117) — a user's mandatory expert not in catalog vanishes with zero record.
→ **Check:** record `dropped_mandatory:[...]`; for find/rate surface as a warning assumption. Silent input-drop is distinct from output_closure (which only guards outputs).

**H14 — `verbal propose-and-confirm` collapses to silent auto-accept in no-TTY.** `user_adjustments:[]` then can't be told from "confirmed as-is."
→ **Check:** `mode_ui ∈ {auto, verbal_confirmed, verbal_downgraded_no_tty}` recorded explicitly; a requested-but-impossible confirm records the downgrade, never masquerades as confirmed.

---

## PHASE 3 — WORK / `rate`  (the weakest branch)

**H15 — `save_rating` is a blind OVERWRITE (persona_spawn.py:71-75).** `r[name] = {"rating":…, "need":…}`. No sample_size, no prior, no blend, no evidence_source, no audit history. **Every §3-rate guarantee (blend-write, never-overwrite-work-earned, evidence-backed) has ZERO code support.** A talk-probe today clobbers any work-earned grade.
→ **Check:** replace with append-and-blend that (a) refuses to write unless the record carries `evidence_source ∈ {work-ledger, cold_start_prior}` + `sample_size`; (b) rejects the write if `prior.evidence_source=="work-ledger" AND new.evidence_source=="cold_start_prior"` (grade-integrity gate); (c) appends an audit entry to `ratings[name].history`. Gate diffs `ratings_before_digest` vs `ratings_after_digest` and asserts only permitted keys changed.

**H16 — The "preferred evidence path" is permanently dead.** `usage.jsonl` is empty at bootstrap and **nothing populates it with findings** — only the spec's own `kind:"selection"` lines. So every `rate` falls back to cold-start field-probe forever; the evidence path never fires.
→ **Check (elevate spec delta #1 to a gate):** work invocations (do/review/build) that use persona P and yield a confirmed finding MUST append `usage.jsonl` line `{kind:"finding", persona:P, …}`. Add cross-invocation test: after such a run, assert the line exists. Without this the whole evidence architecture is theatre.

**H17 — Vacuous score via `parse_judge_score` fallback (persona_ratings.py:16-22).** The second regex grabs **any** number 0-10 anywhere in the judge reply. A judge answer containing "...run these 3 checks" yields score `3` and writes a rating — the `SCORE:` contract is unenforced.
→ **Check:** grade-writes use a **strict parser**: only the labeled `score:` form (first regex) counts; if only the bare-number fallback matched, tag `parse_confidence:"low"` and admit the sample **only as a capped cold_start_prior**, never as work-earned.

**H18 — Judge-independence unenforced.** `request_spec` answers the probe AND judges it — same endpoint/model. Nothing records or compares model identity; the anti-self-grading gate has no code basis.
→ **Check:** record `answer_model` and `judge_model` (actual serving model ids). Gate refuses `judge_model == answer_model`. At `high`, require ≥2 **distinct** judge model ids agreeing within tolerance; disagreement ⇒ **drop the sample**, never blind-average.

**H19 — Thin-answer floor is necessary-not-sufficient.** `_thin = len<40` (lathe.py:1002) is the only substance check; a 40-char generic answer proceeds and, if `s≥0`, writes.
→ **Check:** substance floor gates entry to judging only; the *write* additionally requires strict-parse (H17) + judge-independence (H18); a single low-confidence sample writes as capped cold_start_prior only.

**H20 — `rate` produces nothing silently.** `auto_spawn_for_goal` returns `[]` on any exception (persona_spawn.py:129-132) or empty match; loop rates 0; `return 1`. Per-candidate spawn/license failures (lathe.py:1020-1022) are printed then dropped.
→ **Check:** `cands==[]` ⇒ refuse `refuse_reason:"no_targets_resolved"` (manifest still emitted). Record `targets_attempted` vs `graded` with a per-candidate `drop_reason` (fetch_failed, license_blocked, unmeasurable); a target silently missing from both is a bug the emitter flags.

**H21 — `--all` "resumable skip" never refreshes stale grades.** Line 996 skips any `name in done` forever, even past the recency window — a "complete" run that re-measures nothing.
→ **Check:** skip only if `last_rated` within `recency_window` AND `evidence_source=="work-ledger"`. Stale or cold-start entries stay eligible. Record `skipped_fresh` vs `skipped_locked` counts.

---

## PHASE 3 — WORK / `bucket`

**H22 — `bucket` collapses to one vacuous group.** Line 981 reads `e.get("bucket","specialized")` — the real classifier `bucket_of()` (persona_market.py:4) is **never called**. If catalog entries lack a precomputed `bucket`, all 143 land in `specialized` and "pass."
→ **Check:** when `bucket` field absent, call `bucket_of(name, capability, role)`. Taxonomist-coherence gate: refuse if any single bucket holds >60% of catalog or if `specialized` is the plurality (classifier not wired).

**H23 — Coverage flags vacuously "all never-used."** At empty ledger, high-mode coverage marks all 143 `never_used`.
→ **Check:** distinguish `ledger_absent`/`ledger_empty` from `never_used`; if ledger has 0 entries record `ledger_empty:true`, not `never_used:143`.

---

## PHASE 4 — ADVERSARIAL GATE

**H24 — THE CORE VACUITY: every gate passes trivially on an empty deliverable.** Determinism over `chosen:[]` is byte-identical; output_closure over `[]` is vacuously true; grade_integrity over zero writes is vacuously true. **A run that did nothing passes all six gates.**
→ **Check:** add a `productivity` gate wired to verdict: find⇒`chosen` non-empty OR explicit refuse; rate⇒(`graded` non-empty AND `writes.usage_appended≥1`) OR explicit refuse; bucket⇒`groups` non-empty AND `sum(counts)==catalog_size`. A `pass` with empty deliverable auto-converts to `refuse, refuse_reason:"vacuous_output"`.

**H25 — Gates fail-open on exception.** If unspecified, a throwing gate reads as absent → "pass."
→ **Check:** gate runner initializes every gate to `"error"`; a gate must **explicitly return `"pass"`**; exception leaves it `"error"` ⇒ verdict refuse. `gates.*` ∈ {pass, fail, error, skipped_by_rule:<id>}. `skipped` allowed only where the verb legitimately doesn't run that gate (e.g. grade_integrity on find/bucket) and must carry the rule id — never a bare omission.

**H27 — License/provenance gate is skipped for read-only `find`.** find can *propose* a non-permissive persona whose body is never fetched at selection time; a downstream spawn then rejects it, but the selection already "passed."
→ **Check:** any `chosen` name with `vendored==false` must satisfy `license_ok(license)==true` **at selection time** (fail-closed proposal), so find cannot hand downstream a persona that provenance would later block.

---

## PHASE 5 — MANIFEST

**H28 — No emitter exists; every current return path exits without one.** "Always emitted" is aspirational.
→ **Check:** `cmd_agent` body wrapped so the emit runs in a `finally`; a top-level exception writes a refuse manifest with a traceback digest. Test: force an exception in each verb, assert the manifest file exists and parses.

**H29 — Incomplete manifest passes vacuously.** `tokens:{in:0,out:0}`, `cost_usd:0`, `timing_ms:0`, `models:[]` all default-pass. `rate` calls `request_spec` ≥2×/target yet could report `tokens:0`.
→ **Check:** schema-validate before write (reuse `incomplete_records.py`). Invariant: if any model call occurred ⇒ `models` non-empty AND `tokens.out>0` AND `timing_ms>0`; violation sets `record_incomplete:true` and forbids `verdict:"pass"`.

**H30 — Self-append accounting/ordering.** Append must happen **after** the determinism snapshot (H12), and `writes.usage_appended` must equal lines actually written; a failed append shouldn't silently pass.
→ **Check:** `usage_appended` == real line count; for rate, write ratings then append usage, and if the usage append fails record `write_inconsistency:true`.

**H31 — run_id collision overwrites a prior manifest.** Two runs in the same second → same id → lost record.
→ **Check:** `run_id = ts + short_hash(pid, need_digest, seed)`; emitter uses `safe_write` and refuses to overwrite an existing manifest path.

**H32 — Bootstrap: all three data files are MISSING right now.** Unhardened, first-ever run hits H2 and returns `1` with no manifest — the reflexive tool can't even record its own cold start.
→ **Check:** covered by H2 (refuse manifest on missing catalog) + H23/H16 (empty ledger is a flagged state, not an error).

---

# HARDENED WORKFLOW (implementer spec)

## Typed spine (unchanged order; every step routes through the dispatcher `finally`-emit)

**Phase 0 — Intake (A).** Classify verb {find,rate,bucket,**UNKNOWN**}. Mint collision-safe `run_id` (H31). Resolve thinking level. Load frozen meta-lens literal (H7). Load catalog with integrity probe → refuse on failure (H2). Snapshot ledger digest (H12). Compute `need_digest`, `ambiguous` (H3). *No persona; no grade read.*

**Phase 1 — Front-end (Y, gated).**
- bucket → `status:"skipped_by_rule:bucket-readonly"` (H4).
- find → clarify iff `ambiguous` (<2 canonical tokens); no-TTY records `need_domain=inferred:<tok>`; never blocks.
- rate → assumption-audit on the **two tunable knobs only** (`N_min`, `recency_window`) (H6). `assumption_gate`: unresolved HIGH ⇒ **refuse**, assert ratings digest unchanged (H5). Auto-mode may not self-downgrade HIGH.

**Phase 2 — Selection (A).** Load frozen meta-lens set from `(verb, thinking_level)` **only** (H7). Assert required lens fired (H8). No `load_ratings()`/ledger in scope (regression test with poisoned ratings).

**Phase 3 — Work.**
- **find:** read ledger snapshot → relevance (`score_match`; semantic at high) → `select_score = w_r·relevance + w_g·earned_grade` with cold-start prior **below median, explore-only** (H10) → seeded ε-greedy explore with recorded `seed/roll/skip_reason` (H11) → overlay overrides, recording `dropped_mandatory` (H13) → high-mode `mode_ui` recorded honestly (H14). Empty result ⇒ refuse (H9).
- **rate:** resolve targets, record `targets_attempted` + per-candidate `drop_reason` (H20); empty ⇒ refuse. Evidence path (ledger replay) preferred; field-probe = labeled capped cold-start prior. Strict `SCORE:` parse for writes (H17). Substance floor + judge-independence required (H18/H19). `--all` skip only if fresh+work-earned (H21). Blend-write via new `save_rating` with audit history; never overwrite work-earned with a probe (H15).
- **bucket:** call `bucket_of()` when field absent (H22); high-mode coverage distinguishes `ledger_empty` from `never_used` (H23).

**Phase 4 — Adversarial gate (G, fail-closed).** Gates default `"error"`, must explicitly return `pass` (H25). Set: **productivity** (H24), **determinism** over pinned snapshot (H12), **explore_fired/coverage** with recorded skip reason (H11), **grade_integrity** (H15/H17), **judge_independence** (H18), **license_provenance** at selection time (H27), **output_closure**. Any gate `error/fail` ⇒ `verdict:"refuse"`; rate additionally blocks the ratings write.

**Phase 5 — Manifest (M, `finally`).** Schema-validated (H29), collision-safe non-overwriting write (H31), emitted even on exception/refuse (H28). Self-append one `kind:"selection"` line to `usage.jsonl` **after** snapshot; `usage_appended` reconciled (H30).

---

## Manifest — delta over the proposed schema (added/changed fields marked `+`/`~`)

```json
{
  "run_id": "~ ts+shorthash(pid,need_digest,seed)",
  "invocation": "select-grade-experts", "cli": "agent find|rate|bucket",
  "mode": "find|rate|bucket|+UNKNOWN",
  "thinking_level": "casual|medium|high",
  "+record_incomplete": false,
  "+catalog": { "path":"agents/catalog.json", "size":143, "integrity":"pass|fail" },
  "intake": { "need":"<verbatim>", "need_digest":"sha256…", "ambiguous":false },
  "+ledger": { "path":"agents/usage.jsonl", "present":true, "+snapshot_digest":"sha256…",
               "entries_read":812, "+ledger_empty":false,
               "coverage":{"catalog_size":143,"ever_used":47,"never_used":96,"low_sample":31} },
  "frontend": { "+status":"ran|skipped_by_rule:<id>|blocked",
                "clarify":[{"q":"…","a":"…","source":"user|inferred"}],
                "assumptions":[{"text":"N_min=…","materiality":"HIGH","resolution":"decided:…"}],
                "+dropped_mandatory":[], "assumption_gate":"pass|blocked" },
  "selection_meta": { "meta_lenses":["selection-strategist","assessment-auditor","adversary","taxonomist"],
                      "fired":["selection-strategist"], "+required_lens":"selection-strategist", "why":"…" },

  "find": { "seed":1337, "epsilon":0.15, "+roll":0.09, "+explore_skipped_reason":null, "k":3,
            "considered":[{"name":"…","bucket":"…","relevance":3,"earned_grade":8.4,"sample_size":22,
                           "select_score":11.4,"source":"exploit|explore","picked":true,"reason":"…"}],
            "chosen":["…"], "+mode_ui":"auto|verbal_confirmed|verbal_downgraded_no_tty",
            "user_adjustments":[] },

  "rate": { "+targets_attempted":["…"], "+drops":[{"name":"…","drop_reason":"fetch_failed|license_blocked|unmeasurable"}],
            "+skipped_fresh":0, "+skipped_locked":0,
            "graded":[{"name":"…","evidence_source":"work-ledger|cold_start_prior","sample_size":22,
                       "confirmed_findings_rate":0.68,"severity_weight":1.3,"recency_days":4,
                       "prior_grade":8.1,"prior_evidence_source":"work-ledger","fresh_signal":8.9,
                       "blend_weight":0.4,"new_grade":8.4,"delta":0.3,
                       "+parse_confidence":"high|low","probe_answer_digest":"sha256…",
                       "+answer_model":"…","judge_model":"…","+judge_models":["…","…"],"judge_scores":[9,8]}] },

  "bucket": { "+classifier":"field|bucket_of", "groups":{"security":["…"]},
              "counts":{"security":18}, "+counts_sum":143,
              "coverage_flags":["+ledger_empty|never_used:96"] },

  "gates": { "+productivity":"pass|fail|error",
             "determinism":"pass","explore_fired":"pass|skipped_by_rule:casual",
             "grade_integrity":"pass|skipped_by_rule:find","judge_independence":"pass|skipped_by_rule:find",
             "license_provenance":"pass","output_closure":"pass" },

  "writes": { "ratings_before_digest":"sha…","ratings_after_digest":"sha…","+ratings_write_permitted":true,
              "usage_appended":1,"+write_inconsistency":false,"selection_record":"docs/ce/<run>.selection.json" },

  "models":["…"], "tokens":{"in":0,"out":0}, "cost_usd":0.0, "timing_ms":0,
  "verdict":"pass|refuse", "refuse_reason": null
}
```

## Non-negotiable invariants the emitter/gates enforce (summary)
1. Every code path through `cmd_agent` emits a manifest (`finally`), incl. UNKNOWN/exception/catalog-missing. (H1,H2,H28,H32)
2. `verdict:"pass"` is impossible with an empty deliverable — `productivity` gate converts to refuse. (H24)
3. Gates fail-closed (default `error`, explicit `pass` required). (H25)
4. `rate` writes ratings **only if** grade-integrity + judge-independence + assumption-gate all passed; talk-probe never overwrites work-earned; every write carries evidence_source + audit history. (H5,H15,H17,H18)
5. Determinism is defined over a pinned ledger snapshot, not the live mutating file. (H12)
6. Phase-2 selection reads neither ratings nor ledger — enforced by signature + poisoned-ratings regression test. (H7)
7. `record_incomplete` (models↔tokens↔timing invariant) forbids `pass`. (H29)
8. The evidence path is only real if work invocations append `kind:"finding"` lines — add that cross-invocation gate or `rate`'s preferred path is dead forever. (H16)

The single highest-risk gap for the implementer: **H15/H16** — `save_rating` is a blind overwrite and nothing feeds the ledger, so the entire evidence-weighted-blend architecture is currently unbacked by code. Build the append-and-blend `save_rating` and the finding-append in the work spine first; everything else in `rate` is decoration without them.