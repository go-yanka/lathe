# Persona System — Design Proposal (redesign target)

*Status: proposal from the independent review, at the owner's direction. Documents the honest current state
of the persona subsystem and the target design it should move to. The reviewer authored this; the engine
changes are the maintainer's to implement. Current-state facts are traceable to `agent_router.py`,
`persona_spawn.py`, `persona_ratings.py`, `persona_overrides.py`, `persona_market.py`, and the
`lathe agent` / `review auto` wiring.*

## Verdict on the current module

The persona subsystem is **under-baked**: the machinery exists (a 143-persona catalog, a decider, a rating
command, config overrides) but it is not effectively used, and the pieces don't add up to a system you can
trust or reason about. Specifically:

- Persona **ranking is talk-based, not work-based** — an expert is graded on whether it can *describe* good
  checks in a vacuum, not on whether it ever *found a real defect*.
- **No usage is tracked** — nothing records which personas fire or which never do, so a large tail of the 143
  is dead weight, invisibly.
- **Selection is literal word-overlap** — meaning-blind keyword matching, the same weakness flagged in the
  test-kind gate.
- **Ranking is off by default** — grades don't exist until the user runs an expensive grader, so out of the
  box selection is pure word-overlap.
- **No durable record** of who contributed to a piece of work — the disclosure scrolls past in the terminal
  and is lost.

This document specifies where it should go.

## Design principles (owner's direction)

1. **Grades drive selection.** Which persona is picked must be a function of the grade that persona has
   earned — not a one-off keyword match.
2. **Personas are graded for *work*.** A score is earned by contribution to real outcomes and maintained in
   the system over time.
3. **Grades persist locally, and ship where possible.** The system keeps a local copy of its grades; ideally
   a baseline set of grades travels with each release so a fresh install isn't cold.
4. **Selection has two modes.** An interactive ("verbal") mode where the system proposes which personas it
   would pick for this problem and asks the user — and a fully automatic mode where it just chooses.
5. **Every piece of work produces a report.** Detailed, durable: who contributed, how, and what happened.
   Nothing swept under the carpet.
6. **The number of personas is dynamic.** No rigid floor of two. One, several, or many — chosen by the
   problem and the thinking level.
7. **A thinking-level switch** — casual / medium / high — scales how much brainstorming happens, and
   therefore how many personas are employed.

---

## Target design

### 1. Work-based grading (replace the talker's score)

- **Today:** `lathe agent rate` asks a persona to "list 3 checks in your domain," an LLM judge scores 0–10,
  saved to `agents/ratings.json`. It measures articulation, not results.
- **Target:** a persona earns its grade by **contribution that survives verification** — findings it raises
  in real reviews that are confirmed (not refuted) by an independent check, and, where applicable, that map
  to a gate refusal or a fixed defect. Talk is replaced by a track record.
- **Signal blend (proposal):** `grade = f(confirmed_findings_rate, severity_weight, recency, sample_size)`,
  with a cold-start prior from a light articulation probe so a brand-new persona isn't stuck at zero.

### 2. A grade + usage ledger (persist, and make coverage visible)

- **`agents/ratings.json`** keeps the earned grade per persona (already the file; change what writes to it).
- **New `agents/usage.jsonl`** records every invocation: persona, run id, goal digest, fired/considered,
  findings raised, findings confirmed, timing, model. From this the system can answer, at any time:
  - which personas have **never** been used;
  - each persona's **hit-rate** (confirmed findings per invocation);
  - coverage across the 143.
- **Explore/exploit:** occasionally inject an unused or low-sample persona (epsilon-greedy) so the tail gets
  a fair chance to earn a grade — this fixes both "never used" and cold-start in one move.

### 3. Grades that travel with releases

- Ship a **baseline `ratings.json`** (the maintainer's measured grades) with the release, so a fresh install
  selects intelligently from day one. The user's local copy then **diverges as it learns** on their own work
  (kept local/gitignored, as now). Optionally: a merge step that blends the shipped baseline with local
  evidence.

### 4. Two selection modes: propose-and-confirm, or auto

- **Auto (default):** the system grades-and-picks silently — today's behavior, but grade-driven.
- **Verbal / interactive:** before running, the system says *"for this problem I'd bring in X (security,
  grade 8.4), Y (concurrency, grade 7.1) — accept, or adjust?"* and lets the user swap/add/drop. This makes
  the selection legible and gives the user a lever without forcing them to know the catalog.
- The **mandatory/priority config** (`personas: {mandatory, priority}`) stays as the always-on sticky set,
  layered under both modes.

### 5. A report after every piece of work (the accountability artifact)

One durable manifest per run (`docs/ce/<run>.manifest.json` + a human-readable render), recording:

- the **goal / problem**;
- **every persona considered**, with its match relevance, earned grade, and the reason it was picked or
  skipped;
- **who actually contributed**, and **what each one found** (their findings, verbatim);
- the **gate verdict** and outcome;
- the **thinking level**, model(s), timing, and cost.

This is the "eyeball exactly what was done" record. It pairs with the build's pin-provenance so the *whole*
process — build **and** review — is auditable end to end. Nothing is thrown under the carpet.

### 6. Dynamic persona count (drop the rigid floor of two)

- **Today:** `review` floors at correctness+adversarial (2); `auto_spawn` picks k=2.
- **Target:** the count is **chosen by the problem and the thinking level** — one for a trivial, single-domain
  task; many for a broad or high-stakes one. Two is a possible outcome, not a rule.

### 7. A thinking-level switch (casual / medium / high)

A single dial the user sets (with a sensible **default**), that scales the whole brainstorm:

| Level | Personas employed | Requirement interview | Best-of-N / retries |
|---|---|---|---|
| **casual** | 1 (the single best-matched, highest-graded) | a single interviewer | minimal |
| **medium** (default) | a few, across the relevant domains | one interviewer, thorough | standard |
| **high** | many — several angles brainstorm in parallel | **multiple interviewers**, each probing a different side of the problem, findings merged | maximal |

- This dial should compose with the dials that already exist and mean similar things — assumption scrutiny
  (`off/high/med/all`), `LATHE_TRIES`, per-function `select: N` — ideally a **single user-facing "thinking"
  setting** maps down onto all of them, so the user turns one knob, not five.

### 8. The requirement interview, scaled by thinking

The front-end that interviews the goal (`clarify` + the assumption auditor) is the clearest place the
thinking level should change behavior:

- **casual:** one interviewer asks the fewest, sharpest questions.
- **high:** **multiple interviewer personas** each attack the requirement from a different side (a security
  interviewer, a data-edge interviewer, a user-intent interviewer…), surfacing more of the problem's hidden
  decisions before a line is built. Their questions/assumptions are merged and de-duplicated.
- A **default level** applies when the user says nothing.

---

## Migration notes (for the maintainer)

- The files to evolve, not replace: `agents/ratings.json` (change the writer to outcome-based),
  `persona_spawn.py` (usage ledger + explore/exploit + verbal mode), `agent_router.py` (grade-weighted
  selection; consider a semantic match to fix the word-overlap blindness), `lathe.py` (`review`/`clarify`
  wiring for the thinking switch + the manifest emit).
- The selector should be **stress-tested** (executable probes, like the gates) to confirm the right expert
  actually surfaces for a known-domain input before this ships.
- Backwards-compatible: with no thinking level set, default to **medium**; with no grades present, fall back
  to today's behavior (so nothing breaks mid-migration).

*This proposal is filed to the maintainer as an enhancement; it changes engine behavior and is theirs to
own. The reviewer will stress-test the current selector separately and publish the result.*
