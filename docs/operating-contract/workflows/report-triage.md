I have the grounding I need. The critical confirmations from the code:

- `cmd_flow` (lathe.py:943-944) classifies every AUTO step **purely on exit code** — `classify_step(kind, rc, "")`. A step that returns 0 without doing anything is recorded PASS.
- `"you"` steps in `--run` mode are printed and recorded `'todo'` (line 932) — **not executed, not gated**, and the workflow still verdicts PASS if nothing is BLOCKED.
- `select_agents_for_goal` (agent_router.py) returns `[]` when no `expand_words` token intersects a persona capability. The "CE floor" is asserted in the design but **absent from the router code**.
- `cmd_report`/`cmd_issues` are wired directly in the dispatch table (lathe.py:1702) — they do **not** currently route through any contract; `report` writes a skeleton and returns 0, `issues` is `ls`.

Here is the adversarial critique and hardened spec.

---

# report-triage — adversarial teardown + hardened spec

## 0. The master vector (everything else rides on it)

**W-EXITCODE — the flow runner cannot tell "did the work" from "returned 0."** `cmd_flow` derives every AUTO verdict from `rc` alone (`classify_step(kind, rc, "")`, lathe.py:944). Every auto step in this design — `issues --dedupe`, `build {plan}`, `assume {plan}`, `flow {target} --run` — passes on `rc==0`. A no-op, a cache hit, a fast-fail-swallowed-to-0, or an LLM emitting a placeholder all read as PASS. The entire "output is gated by code" claim is false until this is fixed.

**Deterministic fix (foundational, all steps depend on it): typed receipts.** Each auto/analyst step must write a JSON *receipt* to `docs/ce/<run>/<step_id>.receipt.json` before returning. The flow-runner verdict for a step becomes:
```
verdict = (rc == 0) AND receipt_exists(run,step) AND schema_valid(receipt) AND receipt.did_work == True
```
`did_work` is not a self-report — the receipt schema per step names the *evidence field* that must be non-empty (a resolved path, a captured log ref, a computed number, a validated object). No receipt / malformed / evidence-empty ⇒ step is **BLOCKED**, not passed. This closes H2, H5, H7, H9, H10, H11, H12, H15 at the runner level.

**W-YOU-UNGATED — judgment steps evaporate in autonomous mode.** `"you"` steps are recorded `'todo'` and skipped (line 932). The design's two most important judgments (F1 liaison, T3c classify) are YOU steps, so in autonomous run they produce nothing and the workflow still PASSes. **Fix:** introduce step kind `"judge"` = (analyst LLM call → schema-gate on its structured output). A `judge` step with no analyst output or a schema-invalid object is **BLOCKED**; `workflow_verdict` must treat a BLOCKED central step as **REFUSE**. The current `flow --run` mapping of routing to `flow {target} --run` (which itself skips YOU steps) is therefore invalid for handoff — see H18.

**W-BYPASS — bare commands route around the contract.** `report`/`issues` dispatch straight to `cmd_report`/`cmd_issues`. **Fix:** both become thin shims: `dispatch_contract("report-triage", door, args)`. There is no surviving code path that writes a skeleton or mutates the queue outside the dispatcher. The dispatcher runs the six-phase spine in a `try/finally` where the `finally` **always** emits a manifest (or marks `outcome:"refuse"` with the exception) — a crash still yields a manifest.

---

## 1. Holes, per step, with the deterministic check that closes each

### FILE door

**H1 — manifest not actually guaranteed.** Guard #1 says "every report emits a manifest," but nothing forces it. *Check:* the issue file is written to `<queue>/.staging/<id>.md`, never directly to `open/`. Promotion to `open/` is done **only** by the manifest emitter's post-condition: `assert manifest_exists AND schema_valid(manifest)` then atomic-rename staging→open. No valid manifest ⇒ issue never enters the queue.

**H2 — liaison fills the skeleton with placeholders.** F4 as designed checks "is `## What happened` empty" — trivially beaten by "N/A"/"TODO". *Check:* F4 is a **content** gate, not an emptiness gate:
- `## What I ran / context` must match `^(lathe |python .*engine|engine_v2)\b` OR resolve to a real plan under `plans/` (call `_resolve_plan`; must exist). Prose-only ⇒ `needs-info`.
- Placeholder blocklist (case-insensitive, stripped): `{n/a, na, tbd, todo, none, -, ., see above, unknown, ""}` count as EMPTY.
- Each required field ≥ 12 non-boilerplate chars AND `!=` the skeleton placeholder text.

**H3 — reporter sets severity to duck scrutiny.** Skeleton lets the filer pick `minor`. *Check:* `severity_declared` is advisory and **never** copied to `severity_assessed`. `severity_assessed` exists only after a passed T3c gate; until then it is `blocker`. Manifest carries both, distinctly. Any auto-close consumer reads `severity_assessed` only. Domain ∈ {security, data} floors `severity_assessed ≥ major` regardless of router output.

**H4 — empty domain tag = *less* scrutiny (inverted incentive).** `expand_words(title+body)` can intersect no capability ⇒ domain empty ⇒ security guard never arms, dedupe matches nothing. *Check:* F2 emits a domain from a fixed enum always; empty match ⇒ `domain="unknown"`, which **raises** `thinking_level` and forces the full CE floor. Absent/empty domain may never shrink the reviewer set.

**H5 — provenance attaches nothing but "passes."** F3 runs only if a plan is named; otherwise no-op→0→PASS with empty `provenance`. *Check:* F3 receipt must set `provenance.attached ∈ {run_log|pins|env|none}` + reason. `none` ⇒ `provenance.repro_steps = "UNREPRODUCIBLE: no plan/log referenced"`, a load-bearing value that permanently bars this issue from routing to bug-fix (guard #2). Absence is *recorded as a typed fact*, never swallowed.

### TRIAGE door

**H6 — the entire triage is skippable via bare `lathe issues`.** The design keeps `issues` (no `--triage`) as the old `ls`, contradicting guard #1. A maintainer/agent lists titles and hand-moves files → zero manifests. *Check:* the list door is **pure-read and cannot mutate**. Every state transition (open→resolved/routed/needs-info, triage-block append) is performed only by `commit_transition(run_id, issue_id, new_state)`, which refuses unless a validated manifest for that `run_id` exists. Hand-moves are caught by the `queue_integrity` gate (H14).

**H7 — assumption-auditor waves it through ("no material gaps").** Cheapest passing LLM output. *Check:* T1 gate requires a typed ledger `[{question, materiality∈{HIGH,MED,LOW}, blocks_routing, field_ref}]`. Cross-check against F4 facts: if any of {command, expected, actual, repro} is code-detectably missing, the ledger **must** contain a HIGH item naming that field; a "no gaps" verdict on a demonstrably incomplete report is auto-rejected → step BLOCKED. The auditor cannot clear what code already sees is missing.

**H8 — selection returns zero reviewers.** `select_agents_for_goal` returns `[]` on no token overlap (confirmed). *Check:* `selected = decider_picks ∪ CE_FLOOR`, unioned in code **after** the decider (`CE_FLOOR = {correctness-reviewer, adversarial-reviewer}`). Post-condition `assert CE_FLOOR ⊆ selected AND len(selected) ≥ 2`. Domain ∈ {security, data} force-adds and asserts the domain reviewer. Empty selection is impossible ⇒ BLOCKED before it can happen.

**H9 — dedupe vacuously "unique."** Small/empty token set (H4) or empty queue both yield "unique" with zero real comparison, indistinguishable from a genuine unique. `expand_words` stemming is crude (`ies→y`, `s→∅`), so near-dupes miss. *Check:* dedupe receipt must record `scanned_count` and the **computed** top-N similarity numbers (not absence). `scanned_count==0` ⇒ `unique-uncontested` (distinct state). Require **two** independent signals: normalized-title Jaccard **and** k-gram/MinHash shingling over the body. "unique" needs *both* below threshold; signal disagreement escalates to the router as a MED assumption, never silent-unique.

**H10 — "attempted reproduction" is a lie surface; pin-hit ≠ bug reproduced.** Guard #2 accepts "attempted." A bad plan name fast-fails, or a pin-cache hit rebuilds byte-identical **without exercising the failing scenario** — a green pinned rebuild is evidence the bug is *not* in that unit, yet the design would mark reproduction satisfied. *Checks:*
- `reproduction.attempted=true` only if the runner wrote a receipt with a resolved plan path (asserted to exist), the exit code, and a **non-empty captured log ref**.
- **Split the two facts the design conflates:** `deterministic_rebuild:bool` (pins reused/byte-identical) vs `reproduced:bool` (reported failure actually observed). `reproduced=true` requires a captured failing signal (nonzero test/gate or a diff-vs-expected). Pin-hit + green gates ⇒ `reproduced=false, deterministic_rebuild=true, repro_verdict="could-not-reproduce"`.
- **Route to bug-fix requires `reproduced==true OR failing_test_synthesized==true`.** "attempted but could-not-reproduce" routes to `needs-info`/`question`, never bug-fix.

**H11 — #11 test synthesis is a placeholder (and mapped to the wrong command).** The design calls `assume {plan}` — but `assume` is the assumption auditor, not a test synthesizer (H20). And an LLM can emit `assert False` (trivially fails) or a trivially-passing test; either sets `failing_test_synthesized=true`. *Check:* a synthesized test counts only if the harness **executes** it and observes required polarity under STRICT (matching bug-fix's failing-on-old-code rule, workflows.py:39). `test_ref` must be a file that (a) exists, (b) **fails on HEAD**, (c) references ≥1 symbol defined in the plan's tools module, (d) is **not** a constant/bare assertion (reject if the failing assert has no reference to a plan symbol). Fail any ⇒ `failing_test_synthesized=false`, test discarded.

**H12 — the central classification (T3c) is a YOU step → skipped/ungated.** Per W-YOU-UNGATED it records `'todo'` and the run PASSes with `classification==null`. *Check:* T3c is a `judge` step emitting `{kind∈ENUM, severity_assessed∈ENUM, confidence∈[0,1], rationale, evidence_refs[]}` validated by schema gate. Reject: kind∉enum; `confidence < 0.5` ⇒ forced `needs-info`; rationale < K chars or `evidence_refs` empty (must cite the repro receipt / a dedupe id / a provenance ref). Absent object ⇒ BLOCKED ⇒ `outcome:"refuse"`. A manifest with `classification==null` is INVALID (§3).

**H13 — route is fire-and-forget; child never runs.** `child_run_id` is optional in the design's schema, so "routed_to: bug-fix" can be recorded with no child spawned, or with a child that failed. *Checks:*
- Routing dispatches through `run_contract(child)` (same enforced entry as H6). `child_run_id` is **required** whenever `routed_to ∈ {bug-fix, enhancement, sdlc, clarify}`; parent asserts the child's manifest file exists before recording the route. Absent child_run_id ⇒ invalid manifest.
- Parent records `child_outcome` but does **not** inherit it as its own pass — parent's contract is "handed off correctly," not "fixed."
- `open→resolved` for wontfix/duplicate/question requires a non-empty reason; wontfix on a security-tagged issue additionally requires the `security-reviewer` receipt (guard #3).

**H14 — transition without manifest / partial write / concurrent double-route on the shared queue.** T5 does manifest + mutation; a crash between leaves them inconsistent, and two triage runs on `~/.lathe/issues` both read `open/` and route the same issue. *Checks:*
- **Ordering fixed in code:** write manifest to `<run>.manifest.json.tmp`, fsync, schema-validate, atomic-rename to final; **only then** `commit_transition` (atomic file rename + triage-block append).
- **Per-issue lock:** `commit_transition` acquires `open/<id>.lock` via `O_CREAT|O_EXCL`; a concurrent run aborts. Prevents double-route on the shared queue.
- **`queue_integrity` standing gate** (runs at T0 and T5): every issue's current state must reconcile with the newest manifest naming it; any state change with no manifest (hand-move, H6) or any manifest whose declared transition didn't occur (crash) FAILS it.

**H15 — manifest emitted but hollow (the priority-deliverable failure).** Guard #1 is satisfied by an empty shell (`plan?`, `child_run_id?`, `test_ref?` all absent, `outcome:"pass"`). *Check:* the **Manifest Completeness Contract** (§3) — a schema gate that is the literal last deterministic action; invalid ⇒ nonzero exit, no queue transition.

**H16 — thinking-level as an escape hatch (re-inverts the incentive).** casual makes dedupe "exact-title-slug only" and reproduction "only if plan named" — so a short, plan-less report gets near-zero scrutiny, which is exactly how you'd bury a bug. *Check:* **guards are level-independent; only depth *parameters* read the level.** Domain ∈ {security, data, correctness} OR `severity_assessed==blocker` OR `domain==unknown` ⇒ `thinking_level ≥ medium` (a floor). casual may reduce *breadth* (fewer lenses, pairwise-not-cluster) but can never disable dedupe, the reproduction-attempt, the CE floor, or the adversarial gate.

**H17 — T4 adversarial gate marks itself "held."** The model both raises and clears its own challenge → always `held:true`; `challenge` can be empty/generic. *Check:* T4's hard guards (a: repro attempted; b: security sign-off; c: dedupe ran) are **deterministic code predicates over the receipts**, evaluated independently of the model. Any false predicate FAILs T4 regardless of `held`. The `challenge` string must be non-empty and schema-checked to reference a specific verdict field; `held:false` forces re-route to T3c; `held:true` cannot bypass the code predicates.

**H18 — routing via `flow {target} --run` re-imports the YOU-skip bug.** The child's own critical judgment steps are YOU steps → skipped → child "passes" having done nothing enforceable, and the parent reports a real handoff. *Check:* child dispatch goes through `run_contract` (gated-YOU spine), not `flow --run`. Until a target's spine fully gates its YOU steps, routing to it records `routing.child_outcome="handoff-only"` and the parent may **not** report pass-with-fix — the manifest says "filed for work," not "fixed."

**H20 — command mis-mapping.** The drop-in maps test synthesis to `assume {plan}` (assumption auditor) and reproduction to a bare `build {plan}` (pin hit ≠ repro). Both are category errors; replace per H10/H11 with a dedicated `repro`/`synth-test` action that writes the receipts above.

---

## 2. Hardened workflow (steps + kinds)

Kinds: **A**=auto (gated on rc **and** receipt) · **G**=gate (code predicate) · **J**=judge (analyst call → schema gate) · **M**=manifest. Every A/J writes a typed receipt; the runner verdict is receipt-gated, not rc-only.

### FILE door — `lathe report "<title>"`
| # | Phase | Kind | Behavior + the check it must satisfy |
|---|---|---|---|
| F0 | intake | A | Mint `run_id`; capture project/version/filed_by/ts. Write skeleton to `.staging/`, never `open/`. |
| F1 | front-end | **J** | `bug-reporter-liaison` fills command/expected/actual/repro/impact. Output gated by F4 content gate (H2). |
| F2 | selection | A | Domain from fixed enum; empty match ⇒ `unknown` + raise thinking floor (H4). |
| F3 | work | A | Attach provenance; receipt records `attached∈{run_log,pins,env,none}` + reason (H5). |
| F4 | adversarial gate | **G** | Content gate (H2): missing command/repro ⇒ `needs-info`. `severity_assessed:=blocker` always (H3). |
| F5 | manifest | **M** | Validate manifest → atomic promote `.staging/`→`open/` (H1). Emission is the only path into the queue. |

### TRIAGE door — `lathe issues --triage` (bare `lathe issues` = pure read-only list, cannot mutate — H6)
| # | Phase | Kind | Behavior + check |
|---|---|---|---|
| T0 | intake | A | Load `open/`; run `queue_integrity` gate (H14); set thinking floor (H16). |
| T1 | front-end | **G** | assumption-auditor typed ledger; cross-checked against F4 facts, can't wave through missing fields (H7). |
| T2 | selection | A | `decider ∪ CE_FLOOR`; assert `{correctness,adversarial} ⊆ selected`; security/data force-add domain reviewer (H8). |
| T3a | work: dedupe | A | Two signals (title-Jaccard + body-shingle); record `scanned_count` + numeric similarities; runs **before** route (H9). |
| T3b | work: reproduce | A | Split `deterministic_rebuild` vs `reproduced`; pin-hit ⇒ `could-not-reproduce`. Optional synth-test executed + polarity-checked under STRICT (H10, H11). |
| T3c | work: classify | **J** | Typed `{kind,severity_assessed,confidence,rationale,evidence_refs}`; schema gate; `confidence<0.5`⇒`needs-info` (H12). |
| T3d | work: route | A | Through `run_contract(child)`; `child_run_id` required for bug-fix/enhancement/sdlc/clarify; bug-fix requires `reproduced OR failing_test_synthesized` (H10, H13, H18). |
| T4 | adversarial gate | **G** | Code predicates (repro-attempted, security-signoff, dedupe-ran) evaluated independently of model `held` (H17). |
| T5 | manifest | **M** | Validate manifest (completeness contract) → **then** `commit_transition` under per-issue lock (H14, H15). |

---

## 3. Manifest Completeness Contract (the schema gate — last deterministic action)

Emission FAILS (nonzero exit, no queue transition) unless all hold:

**Always required, non-null:** `run_id, invocation="report-triage", door, intake{raw_args,resolved_skill,thinking_level}, selection{personas[],ce_floor}, gates[]{name,verdict,detail}, contributors[], models[], tokens, timing, outcome`.

**No field may equal its placeholder default.** `severity_assessed != null` and `severity_declared` present-but-distinct (H3).

**Contributor reconciliation (catches skipped/no-op steps):** `contributors[]` must contain exactly one entry per *executed* step (count reconciled against the workflow step list); every entry's `found_or_did` non-empty. A step that ran with no contributor line ⇒ invalid.

**Conditional requireds:**
- `outcome=="pass"` ⇒ `classification, dedupe, reproduction, selection(ce_floor⊆selected)` all present/non-null.
- `routing.routed_to=="bug-fix"` ⇒ `reproduction.attempted==true AND (reproduced OR failing_test_synthesized) AND routing.child_run_id present`.
- `classification.kind=="duplicate"` ⇒ `dedupe.verdict` starts `"duplicate_of:"` **and** that id exists in queue.
- `classification.kind=="wontfix"` on a security-domain issue ⇒ `security-reviewer` receipt present (guard #3).
- `outcome=="refuse"` ⇒ `refusal_reason` non-empty **and** names the failed gate.
- `provenance.attached=="none"` ⇒ `routed_to != "bug-fix"` (H5/guard #2).

**Invocation-specific fields (hardened shape):**
```
issue: { id, title, project, lathe_version, filed_by, filed_at,
         severity_declared, severity_assessed }          # assessed != declared; assessed only after T3c gate
provenance: { plan?, run_log_ref?, pins_ref?, env_snapshot?,
              attached: run_log|pins|env|none, repro_steps }
dedupe: { scanned_count, signals: {title_jaccard, body_shingle},
          nearest: [{id, similarity}], verdict: unique|unique-uncontested|duplicate_of:<id> }
reproduction: { attempted, plan?, command?, log_ref?,
                deterministic_rebuild, reproduced, repro_verdict,
                failing_test_synthesized, test_ref? }     # test_ref proven to fail-on-HEAD + reference a plan symbol
classification: { kind, severity_assessed, confidence, rationale, evidence_refs[] }
adversarial_triage: { challenge, held, code_predicates: {repro_attempted, security_signoff, dedupe_ran} }
routing: { routed_to, target_workflow?, child_run_id?, child_outcome,   # handoff-only|pass|refuse
           owning_plan?, queue_transition }
materiality_rank
```

---

## 4. Hardened, non-bypassable guards

1. **Single enforced entry.** `report`/`issues --triage` route only through `dispatch_contract`; the manifest is emitted in a `try/finally` (crash ⇒ `outcome:"refuse"` manifest). Bare `issues` list is pure-read and cannot mutate.
2. **Receipt-gated steps.** A step's verdict = `rc==0 AND valid non-empty receipt`. No-ops, cache hits, and placeholder LLM output cannot pass.
3. **Manifest-before-mutation, atomically.** Validate manifest → atomic promote/transition under a per-issue lock. No transition without a valid manifest; no manifest-declared transition left undone (`queue_integrity` gate reconciles).
4. **Reproduction truth split.** `deterministic_rebuild` ≠ `reproduced`; bug-fix routing requires `reproduced OR proven failing_test_synthesized`. A harness that never observed the failure cannot route it as a bug.
5. **Fail-closed severity + domain.** `severity_assessed` starts `blocker`, set only by a passed T3c gate; declared severity never trusted; security/data floor to ≥ major; security wontfix needs `security-reviewer` sign-off.
6. **CE floor is code, not decider.** `{correctness, adversarial} ⊆ selected` asserted after the decider; empty selection impossible.
7. **Guards are thinking-level-independent.** casual reduces breadth only; it can never disable dedupe, reproduction-attempt, CE floor, or the adversarial gate; risky domains floor the level to ≥ medium.
8. **Adversarial gate is code predicates, not model self-report.** repro-attempted / security-signoff / dedupe-ran are evaluated over receipts; the model's `held` can only tighten, never loosen.
9. **Route through the child contract, gated.** Children run via `run_contract` (gated YOU), get their own manifest and `child_run_id`; parent reports "handed off," never inherits the child's fix as its own pass.

**Files that must change (implementer):** `lathe.py` (`cmd_report`/`cmd_issues` → dispatcher shims; `cmd_flow`/`classify_step` → receipt-gated, add `judge` kind); `tools/workflows.py` (`report-triage` entry with the F0–F5 / T0–T5 tuples using real actions `repro`/`synth-test`/`run-contract`, not `assume`/`flow --run`); new `tools/triage_manifest.py` (schema + completeness gate + `commit_transition` + lock); new `tools/queue_integrity.py` gate; new `ce_personas/bug-reporter-liaison.md` and `triage-router` lens; extend the decider with an explicit `CE_FLOOR` union.