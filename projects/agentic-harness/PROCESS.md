# LATHE DELIVERY PROCESS — the thinking harness + the implementation harness
*v1.1 — drafted 2026-06-12; CE (Compound-Engineering plugin) integrated 2026-06-16 per owner directive
("integrate CE everywhere that makes sense — added value + more trust in the system"). The implementation
harness stays the deterministic build spine; CE is the design/review front-end woven into the stages below
(see the **CE lane**) — analogous to the design plugin in the UI/UX lane. CE never writes product code.*

**Why this exists.** The implementation harness (plans → engine → gates → pins) is reliable; the
failures that reached the owner were THINKING failures: shallow specs, stub-only proof, data
distributions met for the first time in production, and buggy gates burning generation budget.
Gold in is gold out — this document is the gold-in machine.

---

## Stage 0 — INTAKE & TRIAGE

Every item (feature / bug / enhancement) gets a 5-line intake: intent, who it serves, acceptance
sketch, irreversibility notes, owner-stated uncertainty.

**Triage score:** new user-facing workflow +2 · schema/external-contract change +2 · irreversible
(migration/data-loss risk) +2 · touches matching/ranking correctness +1 · owner states uncertainty +1.

| Score | Route | Cost cap |
|---|---|---|
| ≥4 | **Full council** (Stage 1) | ONE round; no re-convene without new information |
| 2–3 | **Mini-council** (domain + contrarian only) | 2 briefs, 1-page doc |
| ≤1 | **Straight to plan** (Stage 3) | Owner gate = async one-line approve |
| Bug with repro | **Bug lane** (below), no council | — |

Reversible-in-a-day work behind existing gates never sees a council.

## Stage 1 — DESIGN COUNCIL (full-council items)

Parallel role-agents (higher model thinking; the local model never designs). **Anti-echo rules:**

1. **Information asymmetry** — roles see DIFFERENT inputs, not different personas:
   UX gets flows/intent only (no architecture); Systems gets schema/perf budget (no mockups);
   Domain gets the intent + real-world corpus; QA gets the acceptance sketch + the historical
   defect list. Genuine disagreement comes from seeing different things.
2. **Mandatory positions** — every brief MUST contain: top risk · one thing to KILL · one numbered
   objection to the intake's default design. "No objections" is invalid output; regenerate.
3. **Checklists are capped at ~10 items per role** (see Stage 7).

**Role checklists (vQA see §A, vUX §B, vSYS §C below).**

**Stage 1.5 — CALIBRATION DRY-RUN** (mandatory when the item touches matching/extraction/ranking):
run the candidate logic against the **frozen corpus** (`qa/_corpus/` — ~50 real postings, pinned).
Report unmatched %, per-category distribution, top-10 unmapped terms. Unmatched >15% or an empty
category **blocks** promotion to Stage 2. *(This is what would have caught the 38%-unmatched
milestones failure before a line of spec.)*

## Stage 2 — SYNTHESIS → BLIND CONTRARIAN → OWNER GATE

- Analyst synthesizes ONE design doc: decisions, rejected alternatives, unresolved conflicts
  (cross-role conflicts are surfaced, never silently resolved).
- **Contrarian runs AFTER synthesis, blind to the briefs**, attacking the doc itself; seeded with
  the owner's historical corrections (weights-grid rejection etc. — the highest-signal examples).
  Must produce concrete failure scenarios or a signed pass-with-reasons, PLUS a standing **cut list**
  (scope to delete).
- **Owner ratifies ARTIFACTS, not prose:**
  - a **worked example sheet** — real inputs hand-walked to real numbers (the category-model
    negotiation pattern; this is what catches wrong-weights-placement errors),
  - a **static HTML mock** at desktop + 360px (doubles as the model's skeleton and the visual baseline),
  - the **invalidation matrix / contract table** for systems changes,
  - the contrarian's **cut list** — owner explicitly accepts or rejects each cut.
- Low-tier items: async one-line approval. The gate must never queue more than ~2 items; if it does,
  triage was wrong — demote items, don't batch-approve.

## Stage 3 — SDLC TRACE + COVERAGE MAP

FR/TS rows in `qa/REQUIREMENTS.md`, QA-### cases in `qa/QA_PLAN.md`, trace in `qa/RTM.md` — and a
**blocking coverage diff**: every ratified design line maps to a QA case ID or an explicitly
ratified drop. No orphans (the vote-dialog gap class). Every FR carries a ship-status that Stage 6
closes.

## Stage 4 — PLANS (spec + tests; gates are the spec)

- **Plan header convention (CE-grounded):** every non-trivial plan opens with two blocks — **GROUNDING**
  (the real file:symbol(s) it changes, cited — produced via `ce-repo-research-analyst`/`ce-learnings-researcher`
  so specs aren't "plausible but wrong") and **FORKS** (each open decision + the chosen default + the
  alternative, so the owner can redirect before build). Trivial/bug-lane plans may omit.
- QA cases become gates **via the selector contract**: gates bind ONLY to IDs/data-testids declared
  in the plan spec.
- **Gate authoring rules (lintable):**
  1. No source-literal DOM checks for runtime semantics (`'data-x' in content` banned for behavior;
     use DOM evaluation). Structural string checks only for file-level facts.
  2. Text asserts normalize: casefold + whitespace-collapse (CSS text-transform lesson).
  3. No `time.sleep`/blocking calls in route handlers or sync callbacks; waits via `page.wait_for_*`.
  4. Every fixture key the case depends on must be asserted in `seen`; unmatched `/api/**` calls
     fail loudly, never default-ok.
  5. Fixtures load from the **golden pack** (`qa/_golden/` — captured real parser/AI/API outputs),
     never invented shapes. Every fixture links to its recorded source.
  6. Hermeticity declaration per plan: own tmp DB/fixtures, zero reads of live shared state.
  7. Deterministic + time-bounded: identical verdict on 2 consecutive golden runs.
- **GATE CALIBRATION PAIR ("gate-the-gates v2"):** before a gate may judge candidates it is ARMED by:
  golden artifact ⇒ PASS **and** mutant artifact (handler removed / wrong payload) ⇒ FAIL.
  A gate that passes everything is as broken as one that fails everything.

## Stage 5 — ENGINE (local model implements; analyst never hand-edits)

- **Local-first, Claude-as-fallback (owner contract 2026-06-14):** EVERY artifact — including complex pages —
  is tried on the LOCAL model first (`model="openai:g26b"` 26B for skeleton-fill / `gemma4:12b-impl` for
  from-scratch); only after `fallback_after` (default 2) failed gate attempts does the engine escalate to
  `fallback` (e.g. `"claude"`). Claude generation ALWAYS runs through the engine — never hand-written.
- **Deterministic rebuild:** `build_all.py` + pins keyed on sha256(spec+tests+model). Warm rebuild reuses
  pins → test-equivalent reproduction; a pins-cleared rebuild re-samples but gates to converge.
- Failures bank to `_artifact_fails/` + `_fn_fails/` with reasons; analyst sharpens specs.
- **CIRCUIT BREAKER:** three consecutive candidate failures with the IDENTICAL assert signature
  halts generation and re-runs gate calibration — suspicion falls on the judge, not the defendant.
  (Caps gate-bug waste at minutes; the fixture-key bug cost 34 minutes.)
- When a gate is found wrong: fix gate → **re-gate the bank** → pin survivors. Never regenerate
  working candidates.

## Stage 5.5 — CE CODE-REVIEW GATE (after build is green, before DoD) — MANDATORY
Harness gates prove *behavior*; CE reviewers find what behavior-gates can't (exploitable auth paths, edge-case
correctness, scalability, contract breaks). After a plan builds + gates green, the analyst dispatches the CE
reviewer persona(s) selected by the change domain at the DEPLOYED code (`api/app.py` + `agent/*.py`). Reviewers
are **read-only**. A real finding becomes a **failing-first QA-### case in the OWNING plan + a spec/GLUE fix →
regen → re-review** (Stage 5 discipline; never hand-edit generated code). A clean pass — or only owner-accepted
risks — closes the gate.

**Reviewer-selection matrix** (fire all that match the diff):
| Change domain | CE reviewer(s) | Blocking? |
|---|---|---|
| ALWAYS | `ce-correctness-reviewer` · `ce-maintainability-reviewer` · `ce-testing-reviewer` · `ce-project-standards-reviewer` | findings triaged |
| auth / endpoints / permissions / user input | `ce-security-reviewer` | **BLOCKING** |
| large or high-risk diff (auth, payments, data mutation, external API) | `ce-adversarial-reviewer` | **BLOCKING** |
| DB migration / schema / backfill | `ce-data-integrity-guardian` · `ce-data-migration-reviewer` · `ce-deployment-verification-agent` | **BLOCKING** |
| API routes / contracts / serialization | `ce-api-contract-reviewer` | findings triaged |
| queries / loops / caching / I/O | `ce-performance-reviewer` | findings triaged |
| retries / background jobs / async / timeouts | `ce-reliability-reviewer` | findings triaged |
| agent tools / UI actions (agent-native parity) | `ce-agent-native-reviewer` | findings triaged |
| UI page vs design intent | `ce-design-implementation-reviewer` (+ UI/UX lane) | findings triaged |

**BLOCKING** domains cannot ship on a red review. The `circuit-breaker`/`re-gate` discipline from Stage 5 applies
to review-driven regens too. Operationalized by `hreview.py` (logs the review to the activity feed like `hrun.py`).

## Stage 6 — LIVE VERIFICATION (per-feature DoD, not a terminal phase)

- The UX brief's **interaction evidence list** (trigger → immediate feedback → completion evidence →
  live observable) is authored at Stage 1 and becomes the live script verbatim.
- Done = pinned passing gates at every declared level **+** the feature's live wiring-proof green on
  the deployed stack THIS run (live probe; never logs/memory/stub-pass) **+** RTM updated.
- Any gate satisfiable by stubs must declare its paired live assertion.

## Stage 7 — RETRO (the process self-improves, bounded)

- 3 bullets per shipped item: what the council missed, which role owns it.
- **Evict-or-merge rule:** every checklist addition evicts or merges an existing item; hard cap
  ~10/role. Checklists are thinking prompts, not compliance theater.
- Every defect that escaped to live adds a failing-first QA-### case + (if generalizable) a gate rule.
- **Dog-food check:** manually use one shipped feature end-to-end; if it fails despite green gates,
  the gate set is the bug.
- **Process kill criterion:** if after 5 full-council features the owner's gate corrections remain
  the dominant quality source, SHRINK the council — the retro is allowed to conclude the process is
  overhead.

## Bug lane
Failing repro gate in the OWNING plan first → root-cause note → council consult ONLY if design-level
→ fix via spec/GLUE tighten + regen → live verify → retro line. (Per the owner's standing bug-fix
doctrine: never hand-edit generated code; no separate bug-fix harness.)

## Enhancement lane
Mini-council (domain + contrarian) unless it touches the data model (then full).

## UI/UX lane  (any change touching a `*.html` page or `_design.py` — MANDATORY)
Routed through the design plugin (`design:*`); the analyst runs the skills, the local model never does. The
skills are the UI "gold-in"; their repeatable checks are distilled into standing gates.
- **Stage 1 brief:** `design:design-critique` on the current screen feeds the UX brief; `design:design-system`
  if `_design.py` changes; `design:ux-copy` writes/freezes ALL user-facing copy verbatim into the spec (§B-8).
- **Stage 2 ratify:** the static mock is checked against `design:design-system` tokens before the owner gate.
- **Stage 4 gates:** the **design-token lint gate** (fail on off-token hex / off-scale type / box-shadow /
  indigo) is REQUIRED for every UI artifact, armed golden+mutant. A11y via axe/H6.
- **Stage 6 DoD:** `design:design-critique` on the DEPLOYED screenshot + `design:accessibility-review`; new
  findings become failing-first QA-### cases.
- **Distillation rule:** every repeatable design-skill check becomes a $0 standing gate — the skills run at
  milestones, the gates enforce on every build.

## Compound-Engineering (CE) lane  (`compound-engineering:*`) — MANDATORY where it makes sense
CE is the design/review front-end; the harness is the build spine. CE **never writes product code**; `/lfg` and
CE auto-implement stay **OFF**; every CE finding flows back through the harness (fix plan → regen → gate → re-review).
Headless CE runs read-only: `claude -p "/ce-... " --permission-mode plan --max-budget-usd N` (capped); output → `docs/ce/`.
Where CE plugs into the stages:
- **Ground (Stage 3/4 pre-step):** `ce-repo-research-analyst` + `ce-learnings-researcher` cite the real
  symbols + past `docs/solutions/` learnings before a plan is authored → the GROUNDING block.
- **Stage 1 council (high-triage items):** `/ce-plan` (headless, capped) is the system-gap critic and emits
  explicit **FORKS** + a **P0–P3 risk matrix**; CE persona reviewers (`ce-architecture-strategist`,
  `ce-feasibility-reviewer`, `ce-product-lens-reviewer`, `ce-security-lens-reviewer`, `ce-scope-guardian-reviewer`)
  may serve as council roles under the info-asymmetry rule. Forks go to the owner gate (Stage 2).
- **Stage 2 blind contrarian:** `ce-doc-review` / `ce-adversarial-document-reviewer` attacks the synthesized
  design doc (in addition to / as the contrarian).
- **Stage 3:** `ce-spec-flow-analyzer` for flow-completeness / gap discovery on the spec.
- **Stage 5.5:** the **CE review gate** above (reviewer-selection matrix) — the core build-flow integration.
- **Stage 6 DoD:** `ce-deployment-verification-agent` (Go/No-Go + rollback for risky data/migration deploys);
  `ce-design-implementation-reviewer` for UI fidelity.
- **Stage 7 retro:** `ce-compound` writes each solved problem to `docs/solutions/`; future work pulls it via
  `ce-learnings-researcher` (the compounding loop = institutional memory).
- **Per-milestone gap-critic:** a capped headless `/ce-plan` review of the milestone; findings become new gated
  plans. (This caught the `?user=` auth blocker and the extract-on-promotion design — see `docs/ce/`.)
- **Distillation rule:** a recurring CE finding-class becomes a $0 standing gate (e.g. an auth-route lint, a
  "facts in every AI prompt" check) — CE runs at gates/milestones, the standing gate enforces on every build.

---

## §A QA role checklist (cap 10)
1. Which behaviors are unit / integration / e2e-stubbed / live? (No FR on unit alone; every FR ≥1
   integration+ and ≥1 live touch.)
2. What ONE live assertion proves the trigger causes the real effect?
3. Which fixtures, recorded from which real responses? Which page calls are NOT fixtured?
4. Are all asserts behavior-based and normalized?
5. Golden + mutant authored for every gate?
6. What does the stub structurally HIDE that live must observe?
7. Hermeticity: what shared state could this touch?
8. What regression suite must rerun (shared GLUE/artifact edits ⇒ full-suite rerun)?
9. What's the failure budget / circuit-breaker signature set?
10. What QA-### IDs close which FR ship-statuses?

## §B UX role checklist (cap 10)
1. Every surface × {loading, empty, error, success}: exact copy per cell or N/A-with-reason.
2. Async actions: what changes within 100ms of the click; what visible completion/failure evidence?
3. First-run/empty state + call to action?
4. Error copy says what happened AND what to do next?
5. Design-contract delta to `_design.py` declared (or explicitly zero); new layout patterns get DOM
   assertions, not prose.
6. Checks/radios inline (`.check`), lists in `grid2/grid3`, density rules as assertions?
7. ≤760px and 360px behavior: which grids collapse; nav/tabs/chips usable?
8. ALL user-facing copy verbatim in the spec — nothing left to the implementer model.
9. Keyboard reachable, labels associated, sane focus after save/dialog close.
10. What changes on adjacent pages (active tab, chrome, links)?

## §C Systems role checklist (cap 10)
1. Data model & migration: what changes; what does an old-shape record do on read?
2. API contracts: exact schemas + error codes; whose consumers break?
3. Cache/invalidation: event × cache-kind × action matrix; what's read-time vs persisted?
4. AI-call placement: local vs premium per call; calls/job cold AND warm; warm = provably 0-call?
5. Performance budgets: read-time compute bound; background throughput vs ingest rate.
6. Failure modes per external dependency + defined degraded behavior (no silent nulls).
7. Hermeticity: tmp DB, pinned env, golden-sourced stubs?
8. Observability: can persisted state explain every number? Loop alive + single-instance?
9. Cost envelope (tokens, GPU, wall-clock) at 10× current data.
10. Rollback story for the schema/config change.

## Standing artifacts
`qa/_corpus/` — frozen real-posting corpus for calibration runs (pinned, versioned).
`qa/_golden/` — captured real outputs; the ONLY permitted stub source.
`PROCESS.md` — this file; amended only via retro or owner instruction.
design plugin (`design:*`) — analyst-side UX skills (design-critique · design-system · ux-copy ·
accessibility-review · design-handoff); MANDATORY for UI/UX items per the UI/UX lane above.
compound-engineering plugin (`compound-engineering:*`) — design/review front-end per the CE lane above:
`/ce-plan` + persona reviewers (security/correctness/adversarial/data/perf/reliability/api/maintainability),
`ce-doc-review`, `ce-compound`/`ce-learnings-researcher`. Run via `hreview.py` (review gate) + capped headless
`/ce-plan` (milestone gap-critic). Reviews/plans archived in `docs/ce/`; solved-problem learnings in `docs/solutions/`.
`HARNESS_CE_INTEGRATION.md` is the rationale; this PROCESS is the binding spec.
