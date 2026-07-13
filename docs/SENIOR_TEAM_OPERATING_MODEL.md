# Lathe — the Senior-Team Operating Model

> **Thesis:** run AI code generation the way a good engineering team runs a project — with a permanent
> senior crew, phase-appropriate reviews, and judgments that are enforced and looped back — instead of a
> lone LLM that drafts a spec and hopes. This doc stitches the shakedown findings and the follow-on
> enhancements (#45, #48, #49, #50, #51) into one coherent design.

---

## The problem it solves (from the v2.62.6 live shakedown)

A real build exposed four structural gaps (`docs/SHAKEDOWN_v2.62.6_TERMINAL_DRIVE.md`):
- **Scope-collapse (#45):** a complex goal silently became three trivial helpers, shipped "gated-green." The
  gates verify the *drafted spec*, never the *goal vs. the deliverable*.
- **No architecture thinking:** a plan builds exactly one file; decomposition is manual; there's no
  module/folder design (nothing like a package layout).
- **Reviewers are stateless and ad-hoc:** only the Advocate is a permanent persona; the 16 excellent CE
  reviewers are one-shot lenses, picked by a keyword decider, defaulting to just two.
- **Review is advisory:** `lathe review` is read-only; findings archive to `docs/ce/` and only the Advocate
  can block. The good analysis isn't enforced.

The common root: **there's no team.** One model drafts; the machine gates the draft; nobody owns the shape of
the project or is accountable across it.

---

## The crew — what exists vs. what's missing

Three kinds of "always there" (don't conflate them):

| Kind | Member | Real-team analog | Status |
|---|---|---|---|
| Permanent **persona** (charter + memory + authority) | **Advocate** | Product owner / sponsor rep | ✅ exists |
| Permanent **infrastructure** (records every run) | **Reporter** (`dispatcher.finalize` manifest) | PM / scribe | ✅ exists |
| Reactive **mechanism** (fires on failure) | **Healer** (`repair_spec`) | On-call debugger | ✅ exists |
| Permanent **judging seniors** | **App/System Architect · Senior Dev · Senior Tester** | The engineering leads | ❌ **missing → #50** |

The raw talent is already in the catalog (16 curated CE personas + 36 architect/dev/test roles among the
143). What's missing is **lifecycle**: promote the right few from stateless lenses to standing, accountable
team members.

---

## How a project should run (the target lifecycle)

| Phase | Who acts | What they own | Enforcement |
|---|---|---|---|
| **1. Intake** | Requirements Liaison + **framing (#48)** | purpose · users · scope · deliverable · stack · hosting | written to `CLARIFIED_GOAL.md` |
| **2. Architecture (#49)** | **App/System Architect (#50)** | module → file → folder decomposition, `DEPENDS_ON`, layout | human-confirmed `ARCHITECTURE.md`; seeds the plans |
| **3. Spec + tests** | Analyst + **correctness/adversarial on the spec** | testable spec per module | spec-lint + early CE review of the *tests* |
| **4. Assumptions** | Assumption Auditor | the goal's silent choices | assumption gate (blocks on material HIGH) |
| **5. Build** | Implementer (cheap model) + Healer | code that passes the gates | the eight STRICT gates; failures → sharpen spec |
| **6. Review (#51)** | the **applicable CE panel**, conditional-mandatory | correctness/security/reliability/... + triggered specialists | **review gate: fail-closed on P0/P1**, folded into the spec |
| **7. Release** | Senior Tester + Security + Project-Standards + Advocate | coverage, final security, intent | check-in gate; Advocate delivery veto |
| **throughout** | Reporter | the tamper-evident record | every run sealed with a `sha256` |

The Architect (2) is what structurally kills scope-collapse (#45): a goal decomposed into named modules
can't quietly shrink to one helper.

---

## The CE review layer, done right (#51)

Convert `lathe review` from an optional read-only end-step into a **stage-wired, conditional-mandatory,
severity-routed gate**:

- **Conditional-mandatory** — all 16 used *where they apply*, gated by a trigger:
  - *Always-core:* correctness · adversarial · security · maintainability · reliability · testing
  - *Triggered:* api-contract (API changed) · data-migration + data-integrity (schema) · frontend-races
    (async UI) · performance (hot path) · project-standards (release)
- **Severity-routed feedback** — personas already emit **P0–P3 + confidence**. Verify a finding, then:
  **P0/P1 → block + fold into the SPEC → Healer regenerates** (CE sharpens the spec, never edits code);
  **P2 → fold/track; P3 → record.**
- **Enforced** — a review gate that fails closed on unaddressed P0/P1, a peer of the STRICT gates; the
  Reporter records which panel ran and how each finding was routed.

---

## What you can do **today** (no code change)

Pin the always-on CE core so `review auto` runs the good panel on every project — create `lathe.config.json`
at the repo root (precedence: env > config > default):

```json
{
  "personas": {
    "mandatory": ["correctness", "adversarial", "security", "testing"],
    "priority":  { "reliability-reviewer": 2.0, "maintainability-reviewer": 1.5 }
  }
}
```
And prefer meaning over keywords when selecting the rest:
```bash
LATHE_DECIDER_MODE=semantic lathe review auto <files>   # smart panel
lathe review all <files>                                # the full gauntlet
```
This is config-pinned (always *consulted*) but still stateless — the standing, memory-carrying team is the
#50 change.

---

## The roadmap in one line

**#48 (know the project) → #49 (structure it) → #50 (a standing senior team) → #51 (their judgment is
enforced and looped back)** — with **#45** as the failure that proves why all four are needed.

Advice becomes discipline only at #51: the same reason Lathe's whole premise works — *a check that can't be
skipped* — applied to the team, not just the tests.
