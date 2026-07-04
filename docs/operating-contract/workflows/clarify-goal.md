I have the full surface. Here is the adversarial critique and hardened spec.

---

# Adversarial critique — `lathe clarify` workflow

## Verdict up front

The proposed workflow has **one structural design flaw** and **~18 vacuity holes**. The load-bearing weakness: as written, the phase-4 "adversarial gate" is a **lint, not a gate** — it never fails closed, so a brief containing one keyword-stuffed acceptance criterion and zero real content produces `verdict:pass, design_ready:true`, which `do`/`sdlc` then trust. Every model call in the chain routes through `request_spec`, which **returns `""` on any failure and never raises** (`request_spec.py:80-81`), so the entire interview can silently evaporate while the manifest still reports success. Below, every hole is paired with the deterministic check that closes it.

---

## Part A — Holes, ranked by blast radius

### H1 — The gate cannot fail (design is decorative). **[critical]**
The spec says "clarify never hard-blocks... advisory," and the sample manifest shows `verdict:warn → design_ready:true`. So the only path to `refuse` is analyst-down/empty-brief. An adversary (or a lazy analyst) emits a brief with `Refined goal: do the thing` + one criterion `returns the correct result` — the `criteria_testable` heuristic matches the verb `returns`, count≥1 passes, `design_ready:true`. Downstream proceeds on garbage.
**Closer:** `criteria_testable(brief)` must return a **structured verdict, and `design_ready` must be a conjunction of hard predicates**, not "brief non-empty":
```
design_ready = refined_goal_present
           AND refined_goal_reduced_ambiguity     # H2
           AND criteria_count >= 1
           AND every criterion passes falsifiability (H7)
           AND auditor_ran == True                 # H16
           AND high_assumptions_open == 0          # unresolved HIGH forces False
```
`warn` (design_ready may still be true) is reserved for MED/LOW open items only. Any HIGH-materiality unresolved assumption → `design_ready:false`, verdict `warn-blocking`. Empty/failed brief → `refuse`, return 1. **`do`/`sdlc` must refuse to start on `design_ready:false`** (add the check at their intake, not just read the flag).

### H2 — Clarify can "succeed" without reducing any ambiguity. **[critical]**
Nothing checks that the output is *less vague than the input*. `request_spec` blips → 0 questions → 0 answers → brief synthesized from the goal alone → `Refined goal:` is a restatement of the original vague goal.
**Closer:** deterministic self-consistency check `ambiguity_residue(goal, brief)`: run the **existing `goal_vagueness()` on the `Refined goal:` line**. If `needs_clarify` was `True` for the original goal and is *still* `True` for the refined goal, clarify did not do its job → `design_ready:false`. Record `vagueness_before` / `vagueness_after` in the manifest. This reuses code that already exists and is impossible to satisfy vacuously.

### H3 — `request_spec` returns `""` on every failure; no call is guarded. **[critical]**
Question-generation (`:1421`), each per-interviewer call, synthesis (`:1463`), and the auditor (`:1473`) all silently degrade to `""`. Only synthesis has a guard (`:1464`). A transient proxy restart mid-interview yields a brief built on nothing while the manifest shows `outcome:pass`.
**Closer:** wrap every analyst call in a recorded result object `{ok:bool, text, err, tokens, model}`. A call with `ok:false` (empty return, or `"API Error"`/`"API_ERROR"` substring) is recorded as a **failed contributor**, and the phase's guard (H18, H16) decides refuse vs. degrade. Never let `""` flow silently into the next phase.

### H4 — The "domain interviewers" don't exist; reviewers are miscast as interviewers. **[high, design]**
The proposal fans out by prompting selected personas with the liaison's *question* prompt — but the catalog personas are **reviewers** (`security-reviewer`, `performance-reviewer`, `data-integrity-guardian`), authored to emit *findings*, not to *interrogate a user*. Injecting `security-reviewer.md` into "produce clarifying questions" is off-label; the model may emit review findings, refuse, or restate the goal. Nothing validates the output is actually interrogative.
**Closer, two parts:**
(a) **Output-shape gate** `is_interview_output(text)`: reject any interviewer output where <50% of kept lines are interrogative (`parse_questions` already extracts `?`/numbered lines — require `len(parsed_questions) >= 1` AND each retained question ends in `?` OR carries an `[options:…]` marker). Findings-shaped output (declarative lines, `[ASSUMPTION|…]` markers) → that interviewer contributes `asked 0`, recorded as `off_shape:true`.
(b) The manifest must record `role:"domain-reviewer-as-interviewer"` so the design smell is visible, not hidden behind `role:"domain"`.

### H5 — Decider silently returns 0 domain interviewers; N is a lie. **[high]**
`select_agents_for_goal` requires `score > 0` (`agent_router.py:71`) — an off-domain goal (no capability-word overlap) returns `[]`. So "high = 5 interviewers" degrades to **1 (liaison only)** with no error, and the manifest's `interviewer_budget:5` contradicts `interviewers:[liaison]`.
**Closer:** the manifest must record **both** `interviewer_budget` (requested) and `interviewers_fired` (actual, len of successful contributors), and a `budget_met:bool`. The gate does **not** require budget_met (off-domain goals legitimately have no specialists) — but it **does** require: if `needs_clarify` and `interviewers_fired == 0` → `refuse` (H18). The lie is closed by recording actuals separately from the dial.

### H6 — `parse_questions` accepts prose and non-questions. **[high]**
It keeps any line ending in `?` *or* starting with `\d+[.)]`/`[-*]`/`Q\d+` (`clarify_logic.py:27`). "1. I have reviewed the goal." is kept as a "question." "NO QUESTIONS" sentinel is only checked in the first 40 chars of the *whole* raw text (`:1422`), so an interviewer that emits a paragraph then "no questions" bypasses it.
**Closer:** tighten to `question_lines(text)`: a line qualifies only if it ends in `?` **after** stripping the `[options:…](default:…)` tail. Numbered-but-not-interrogative lines are dropped. Sentinel check becomes per-line: drop any line matching `^\s*(no questions|none|n/?a)\b` case-insensitive regardless of position. Record `raw_lines` vs `kept_questions` count so silent over/under-parsing is visible.

### H7 — `criteria_testable` uses the same spoofable verb heuristic as lint-spec. **[high]**
"has a checkable predicate — number/comparison/`returns|rejects|equals|within`" is satisfied by `returns the right value`, `equals what is expected`, `within acceptable limits`. Keyword-stuffing passes.
**Closer:** raise the bar to **two independent signals per criterion**: (1) an interrogable predicate token AND (2) a **concrete referent** — a literal (number, quoted string, code identifier, path, format name) OR an explicit input→output pair (`->`, `given…then`). A criterion with a predicate verb but *no* concrete referent → `testable:false`. Record `criteria_testable` as `[{text, predicate:bool, referent:bool, pass:bool}]`, not a bare count, so the vacuous ones are named.

### H8 — Cost/model instrument is structurally always-zero. **[high]**
`request_spec` extracts `d["choices"][0]["message"]["content"]` and **discards `d["usage"]` and `d["model"]`** (`request_spec.py:69`). The manifest's `tokens:{in:0,out:0}`, `cost.usd:0`, and `models.analyst` are therefore **incapable of being populated** — the "evaluation instrument" is blind on cost and on which model actually answered.
**Closer (code delta, mandatory):** add `request_spec_metered(prompt, ...) -> {text, usage:{in,out}, model, ok, err}` (or extend `request_spec` to optionally return the envelope) that surfaces `d.get("usage")` and `d.get("model")`. The manifest records the **echoed** model per call, sums real tokens, and computes `usd` from a price table. If the endpoint returns no `usage`, record `tokens:null` and set `cost.metered:false` — an explicit "unknown," never a fabricated 0.

### H9 — No manifest on the failure/short-circuit/exception paths. **[high]**
The `return 1` at `:1465` and the "already clear" branch at `:1407-1409` emit nothing today; an uncaught exception anywhere emits nothing. The spine's core promise ("ALWAYS emitted") is violated on exactly the paths that matter most (refusals).
**Closer:** structure `cmd_clarify` so `run_id`, `ts_start`, and a `manifest` dict are minted in phase 0, and a **single `finally` block writes `docs/ce/<run_id>.manifest.json` + render on every exit path** (pass, warn, refuse, exception). Wrap the body in `try/except Exception as e:` → record `outcome:"error"`, `error:str(e)`, still emit, `return 1`. A test must assert: for each of {clear-goal, analyst-down, exception-injected}, the manifest file exists and has `outcome` set.

### H10 — Manifest write location can fail *after* spend, losing the record. **[med]**
`os.makedirs(out_dir)` (`:1486`) runs only after all model calls. If `--out` is unwritable, the run spends tokens then dies with no artifact. And if `docs/ce/` is unwritable, no manifest anywhere.
**Closer:** phase-0 preflight `assert_writable(docs/ce)` and `assert_writable(out_dir)` **before** any analyst call; on failure `refuse` immediately (return 2) — cheap, no spend. `docs/ce/` is the guaranteed record sink and is validated first; `CLARIFIED_GOAL.md` to `--out` is validated second.

### H11 — Auditor skip is indistinguishable from "no assumptions found." **[high]**
Current code swallows all auditor failure in `try/except: pass` (`:1484`). `_led == []` means *either* the auditor cleanly found nothing *or* the endpoint blipped. An adversary who kills the auditor endpoint gets `high_assumptions_open:0 → verdict pass`, i.e. the adversarial phase is bypassed by making it fail.
**Closer:** record `auditor_ran:bool` (call `ok:true`) separately from `assumptions:[]`. Gate rule: `auditor_ran == false` → **cannot be `pass`**; verdict is `refuse` (strict) or `warn` with `audit_failed:true, design_ready:false`. The adversarial phase must *run*, not merely be attempted.

### H12 — `merge_questions` string-dedup can't catch paraphrase, and the cap is non-deterministic. **[med]**
The existing dedup is exact-string (`seen` set, `:38`). Two interviewers asking "Which encoding?" vs "What character encoding is assumed?" both survive → user answers twice, `criteria_count` inflated. And "cap at max_questions" without a defined ordering/tie-break is non-deterministic across dict-iteration order — violating the harness's determinism principle (#9).
**Closer:** `merge_questions(per_interviewer_lists, max_questions)`:
- canonicalize (lowercase, strip punctuation/stopwords) → dedup on canonical key;
- **deterministic ordering**: sort by `(floor_first, interviewer_rank, original_index)` so the liaison's questions win ties and output is stable given inputs;
- cap keeps the top `max_questions` by that order; record `dropped:[…]` with reason;
- **floor guard**: if any questions existed pre-merge, post-merge count must be `>= 1` (a dedup bug can't zero the interview).
Record `raw_count`, `merged_count`, `dropped_count`, and per-question `askers:[…]`.

### H13 — Answer coverage is unchecked; short `--answers` files pass silently. **[high]**
`raw = scripted[i-1] if i-1 < len(scripted) else ""` (`:1443`) → questions past the file length get empty answers, coerced to default or "". In autonomous mode the spec says "an analyst call answers from context, and that output is itself gated" but **defines no gate**. Result: brief synthesized from mostly-empty answers, `design_ready:true`.
**Closer:** compute `answered = count(chosen != "" and chosen is not just the echoed default with no signal)`; record `answer_coverage = answered / questions_fired`. Gate rule: if `needs_clarify` and `answer_coverage < threshold` (e.g. <0.5) and no HIGH assumption was resolved by the answers → `warn`, `design_ready:false` (the interview was not actually conducted). For autonomous mode, the "analyst answers" output is run through the **same** `question_lines`/coverage check — an answer set that doesn't address the questions fails coverage.

### H14 — `run_id` hash collision overwrites prior manifests. **[med]**
`clarify-<UTC>-<hash8>` — if `hash8` is of the goal, re-clarifying the same goal overwrites the earlier run's manifest (losing the audit trail); if of the timestamp, fine but must be specified. Sub-second reruns can collide on a coarse UTC stamp.
**Closer:** `run_id = clarify-<UTCyyyymmddThhmmssZ>-<hash8(goal + ts_start_ns + os.getpid())>`. Manifest write is **create-exclusive** (`open(..., 'x')`); on the astronomically-rare collision, suffix `-1`. Never overwrite an existing manifest.

### H15 — `goal_vagueness` short-circuit is keyword-spoofable and under-emits. **[med]**
`needs_clarify` is `False` if the goal merely *contains* an inputs-word and an outputs-word (`clarify_logic.py:16-17`). "return the input" (5 words → actually flagged too-brief, ok) but "the function will take the input and return an output for the user somehow" passes as clear while being vacuous.
**Closer:** the short-circuit must **still run the full spine** (selection→work→gate→manifest) — the spec says this, and it's right — but additionally the manifest must record `short_circuit:true, short_circuit_basis:"keyword-heuristic"` and **still run the auditor** (H11). A "clear" goal that the auditor flags with a HIGH unstated assumption flips `design_ready:false`. The keyword short-circuit may skip *questions*, never the *audit* or the *gate*.

### H16 — "high scrutiny second devil's-advocate pass" is unverifiable. **[med]**
The `high` thinking level promises "a second devil's-advocate pass challenging each criterion," but nothing checks the second pass *ran* or *challenged anything* — the dial can claim `high` and deliver one pass.
**Closer:** record `audit_passes_run:int` and, for high, require `audit_passes_run == 2` in the manifest (recorded actual, not the dial's intent). Each pass records its own contributor line with tokens. `budget_met`-style `scrutiny_met:bool`. Not gate-blocking (scrutiny is depth, not correctness) but **auditable** so a dishonest run is detectable.

### H17 — "why" for each selection can be vacuous / null-degraded. **[low]**
Sample shows `match:6.0, rating:7.2` but `score_match` returns a small integer overlap and `ratings.json` may lack these personas → `rating:null`, and `match×rating` ranking silently degrades to `match×1`.
**Closer:** record per-pick `{match:int, rating:float|null, rating_source:"ratings.json"|"default-1.0", why:str}` where `why` is generated deterministically from the matched capability tokens (`"goal tokens {auth,token} ∩ capability → bucket=security"`), never free-text. A pick whose `why` has zero matched tokens is invalid (that's the H5 case).

### H18 — No floor guarantee that *any* interview happened on a vague goal. **[critical — the composite]**
Combining H3+H5+H6: vague goal + liaison endpoint blip → `questions:[]` → `answers:[]` → brief from goal → all keyword gates pass → `design_ready:true`. The single most damaging path.
**Closer (the spine floor):** deterministic invariant enforced in code, non-bypassable:
```
if needs_clarify and questions_fired == 0:
    verdict = "refuse"; design_ready = False; return 1
if interviewers_fired == 0 and any(contributor.ok is False):
    verdict = "refuse"   # every interviewer failed → analyst is down, not "goal was clear"
```
This distinguishes "goal genuinely needed no questions" (auditor also clean) from "we asked nothing because the analyst was unreachable."

---

## Part B — Hardened workflow (typed, with inline guards)

| # | Phase | Type | Action + **GUARD (deterministic, in code)** |
|---|---|---|---|
| 0 | Intake | AUTO | Parse args; mint `run_id`+`ts_start` (H14); resolve `--think` → `(budget, rounds, max_q, scrutiny)` clamped to known set, record `source`. **G0a:** `assert_writable(docs/ce)` and `assert_writable(out_dir)` before any spend (H10) → refuse(2) on fail. **G0b:** init `manifest` dict + register `finally`-writer now (H9). Run `goal_vagueness` → record `vagueness_before`, `short_circuit` (H15). |
| 1 | Selection | AUTO | Floor `requirements-liaison`; `select_agents_for_goal(goal, caps, budget-1)`. Record `interviewer_budget` vs `interviewers_planned`, per-pick `{match,rating,rating_source,why}` (H17), `role:"domain-reviewer-as-interviewer"` (H4b). `budget_met:bool` (H5). |
| 2a | Work | AUTO | Fan out `request_spec_metered` per interviewer (H8). **G2a:** each output → `is_interview_output` (H4a) + `question_lines` (H6); failed/off-shape → contributor `ok:false, off_shape` recorded, not silently dropped (H3). |
| 2b | Work | AUTO | `merge_questions` — canonical dedup, **deterministic order + tie-break**, cap, provenance, **floor guard** post-merge≥1 if any existed (H12). |
| — | Floor | GATE | **G-FLOOR (non-bypassable):** `needs_clarify and questions_fired==0` → refuse (H18). `all interviewers ok:false` → refuse. |
| 2c | Work | YOU | Answer once. **G2c:** compute `answer_coverage`; autonomous answers run through same shape check (H13). |
| 2d | Work | AUTO | Synthesize brief (metered). **G2d:** empty/`API Error` → refuse (existing `:1464`, kept). |
| 3a | Adv. gate | AUTO | Auditor pass(es), metered. **G3a:** record `auditor_ran`, `audit_passes_run` (H11,H16); `auditor_ran==false` → cannot be `pass`. |
| 3b | Adv. gate | GATE | `criteria_testable` (two-signal, H7) + `ambiguity_residue` (H2) + HIGH-open check. Compute `design_ready` as the **conjunction** in H1. Verdicts: `pass` / `warn` / `warn-blocking`(design_ready:false) / `refuse`. |
| 4 | Manifest | AUTO | `finally`-write `docs/ce/<run_id>.manifest.json` (create-exclusive, H14) + md render + `CLARIFIED_GOAL.md`, **on every path incl. exception** (H9). |

Downstream contract change: `do`/`sdlc` intake **must** read `design_ready`; `false` → bounce back, don't proceed (H1).

---

## Part C — Hardened manifest fields (additions/changes over the proposal)

Keep the proposed schema; **add/replace** these load-bearing fields (starred = new guarantee):

```jsonc
"intake": {
  "goal": "...", "short_circuit": false,
  "short_circuit_basis": "keyword-heuristic",        // * H15
  "vagueness_before": {"needs_clarify": true, "missing": [...]},
  "writable_preflight": {"docs_ce": true, "out_dir": true}   // * H10
},
"thinking": { "level":"high","source":"--think",
  "interviewer_budget":5,"rounds":2,"max_questions":7,"audit_scrutiny":"max" },
"selection": {
  "floored":["requirements-liaison"],
  "interviewers":[ {"name":"security-reviewer","role":"domain-reviewer-as-interviewer",  // * H4b
     "match":6,"rating":null,"rating_source":"default-1.0","why":"tokens {auth,token} ∩ cap; bucket=security"} ],  // * H17
  "interviewers_planned":5, "budget_met":false        // * H5
},
"contributors":[ {"step":"2a","actor":"security-reviewer","ok":false,   // * H3
   "off_shape":true,"did":"returned findings, not questions; 0 kept",
   "model":"claude-sonnet-4-...","tokens":{"in":812,"out":40}} ],       // * H8 echoed model+real tokens
"questions_stats": {"raw_count":9,"merged_count":5,"dropped_count":4,    // * H6/H12
   "questions_fired":5,"interviewers_fired":2},
"answers_stats": {"answered":4,"answer_coverage":0.8},                   // * H13
"audit": {"auditor_ran":true,"audit_passes_run":2,"scrutiny_met":true,   // * H11/H16
   "assumptions_total":4,"high_open":1},
"gate": {
  "name":"criteria-testability","verdict":"warn-blocking",              // * H1 new verdict
  "checks":{
    "refined_goal_present":true,
    "ambiguity_residue":{"vagueness_after":{"needs_clarify":false},"reduced":true}, // * H2
    "criteria":[ {"text":"...","predicate":true,"referent":true,"pass":true} ],     // * H7 per-criterion
    "criteria_count":5,"criteria_testable":4,
    "auditor_ran":true,"high_assumptions_open":1 },
  "design_ready": false,                                                 // * H1 conjunction
  "reason":"1 HIGH assumption unresolved -> design_ready withheld"
},
"cost": {"metered":true,"tokens_in":0,"tokens_out":0,"usd":0.0,"calls":6}, // * H8 metered flag; null if endpoint gave no usage
"outcome": "warn"   // one of pass|warn|refuse|error  — set on EVERY path incl. exception (H9)
```

---

## Part D — Deterministic functions the implementer must build (signatures)

New in `clarify_logic.py` (all pure, ≥4 asserts, per doctrine):
- `question_lines(text) -> list[str]` — interrogative-only, per-line sentinel (H6).
- `is_interview_output(text) -> bool` — ≥1 question AND ≥50% interrogative (H4a).
- `merge_questions(per_interviewer: list[tuple[str, list[str]]], max_questions:int) -> {kept, dropped, askers}` — canonical dedup, deterministic order/tie-break, floor guard (H12).
- `criteria_testable(brief) -> {criteria:[{predicate,referent,pass}], count, testable}` — two-signal (H7).
- `ambiguity_residue(goal, brief) -> {vagueness_after, reduced}` — reuse `goal_vagueness` on the refined line (H2).
- `answer_coverage(questions, answers) -> float` (H13).
- `clarify_verdict(checks) -> {verdict, design_ready}` — the H1 conjunction; the single source of the gate decision.

Changed in `request_spec.py` (or new wrapper): `request_spec_metered(prompt, ...) -> {text, ok, err, usage, model}` surfacing `d.get("usage")`/`d.get("model")` currently discarded at `request_spec.py:69` (H8).

Changed in `lathe.py:cmd_clarify`: phase-0 preflight + `finally`-writer wrapping the whole body (H9/H10); floor gate G-FLOOR (H18); promote auditor out of `try/except:pass` at `:1470-1485` into a recorded, gated contributor (H11).

Referenced files (absolute): `/home/user/lathe/lathe.py` (`cmd_clarify` @1381, `cmd_review` decider @264-302), `/home/user/lathe/projects/agentic-harness/tools/clarify_logic.py`, `/home/user/lathe/projects/agentic-harness/tools/request_spec.py` (usage discarded @69), `/home/user/lathe/projects/agentic-harness/tools/agent_router.py` (`select_agents_for_goal` @59, `score>0` @71), `/home/user/lathe/projects/agentic-harness/tools/assumption_logic.py`, `/home/user/lathe/projects/agentic-harness/tools/workflows.py` (add `clarify` entry + contract), `/home/user/lathe/docs/OPERATING_CONTRACT_DESIGN.md` (Part 2 item 10 @102).

**The single most important fix:** H1+H18 together — make `design_ready` a conjunction of hard predicates and make an interview that produced nothing on a vague goal a `refuse`, not a `pass`. Without those two, every other gate is theater because the workflow's own success signal is unfalsifiable.