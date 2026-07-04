# Lathe — Operating Contract & Per-Invocation Workflow Design

> **✅ STATUS — IMPLEMENTED (v2.10.0–v2.13.1).** This design was built and verified; see
> `operating-contract/IMPLEMENTATION_SPEC.md` for the shipped-version map. Retained as the design record.

*Design proposal (owner-directed). The problem: Lathe exposes ~35 commands but only 6 have a designed
workflow, none are enforced, and none emit a uniform record — so how the harness operates per invocation is
inconsistent and unauditable. This doc (1) defines a single **operating contract** every invocation runs
through, (2) designs the **ideal workflow per invocation**, and (3) fixes the **code vs skill vs data** split
for implementation. Grounded in the real CLI surface and `workflows.py`. This is the "design first" step; skills
+ deterministic code come after.*

## Guiding principle (the code/skill split)

> **Anything that must be *guaranteed* is deterministic code. Anything that requires *judgment* is a skill
> whose output is gated by code. If a guarantee depends on the model choosing to follow instructions, it
> isn't a guarantee — move it into the dispatcher.**

This is Lathe's own thesis turned on itself: don't trust the model to run the procedure, put a deterministic
orchestrator around it. A skill raises the floor; only code makes it a "sure shot."

---

## Part 1 — The uniform operating contract (every invocation runs through this)

Every invocation, whatever its type, passes through the **same six-phase spine**. The spine is deterministic
code (the dispatcher); the *content* of each phase comes from the invocation's skill (a data-defined
workflow) and from model judgment inside gated steps.

| Phase | What it does | Layer | Guaranteed output |
|---|---|---|---|
| **0. Intake** | classify the invocation, resolve its skill, set the thinking level (casual/medium/high → depth) | code | a run id + resolved plan |
| **1. Front-end** | clarify goal / audit assumptions where the invocation writes or changes behavior | skill+model, gated | recorded questions/decisions |
| **2. Selection** | pick the personas/lenses for this job (grade-weighted, explore/exploit — issue #9) | code (mechanics) + data (catalog) | the chosen set + why |
| **3. Work** | the actual steps (build / review / verify / …) — typed `auto`/`gate`/`you` | skill defines, code runs, model fills | each step's result |
| **4. Adversarial gate** | the harness tries to break its own output (issue #11); gates must pass | code enforces, model generates cases | pass/fail + what was tried |
| **5. Manifest** | emit the per-run record: intake, selection+why, each contributor + finding, gate verdicts, thinking level, model, cost | **code — never optional** | `docs/ce/<run>.manifest.json` + render |

**Non-negotiables, all in code:** the invocation cannot run *around* its skill (bare `lathe do/review/…`
*is* the contract); step order and gate pass/fail are enforced; the manifest is always written. The skill can
be edited freely (it's data); it can never disable the spine.

**Thinking level** scales phases 2–4: `casual` = 1 persona, one front-end pass, minimal adversarial; `medium`
(default) = a few personas, thorough front-end; `high` = many personas in parallel, multi-interviewer
front-end, maximal adversarial. One dial, mapped down onto `LATHE_TRIES` / `select:N` / assumption scrutiny.

---

## Part 2 — The ideal workflow per invocation

Notation from `workflows.py`: **A** = `auto` (a gated `lathe` subcommand), **G** = `gate` (standing check
that must pass), **Y** = `you` (a judgment step; in autonomous mode an analyst call whose *output* is gated).
Every workflow ends with **M** = the manifest (phase 5), always emitted.

### Creation intents

**1. Build from a goal** (`do` / `"<goal>"` / `chat`)
`Y/A clarify goal → A assumption-audit (HIGH blocks) → A analyst writes plan (spec+tests) → G spec-lint (tests
pin behavior) → A generate under gates (best-of-N) → G STRICT gates → G adversarial-test synthesis (#11) →
A pin + assemble → G standing regression → M`.
*Guard:* refuse to finish if the goal was vague and no clarify ran; refuse to pin if adversarial tests weren't
generated.

**2. Build from a plan** (`build`)
`G validate plan is data-only → G spec-lint → A generate under gates → G STRICT gates → G adversarial synth →
A pin → G standing regression → M`.
*Guard:* a fully-pinned plan short-circuits to pin-replay (0 model calls) but still emits M.

**3. Autonomous objective** (`auto` / `run` / `decompose`)
`A decompose objective → board tasks (+deps) → loop[ build-from-plan workflow per task → on fail: bank +
sharpen spec (no escalation) ] → G cross-task regression → Y/A owner gate before commit (LATHE_AUTO_COMMIT) →
M (per task + rollup)`.
*Guard:* no commit without the owner gate; every task gets its own manifest.

**4. Add a feature / enhancement** (existing `enhancement`)
`Y/A clarify scope → A SDLC trace (new FRs → tests) → build-from-plan workflow → G no-regression on siblings →
code-review workflow on the diff → Y release → M`.

### Correction intents

**5. Fix a bug** (existing `bug-fix`)
`A reproduce (rebuild failing plan, capture log) → A diagnose from trace (spec bug or impl?) → G lint-spec (are
the tests even good?) → Y/A fix the SPEC to reproduce the bug → A assumption-audit → A rebuild under STRICT
(must ship a failing-on-old-code test) → G clean+no-regress → code-review workflow → Y release → M`.

### Review / verification intents

**6. Review a code change** (existing `code-review`, `review auto`)
`A decider selects reviewer personas (graded, #9) → parallel persona reviews → A adversarial-verify each
finding (kill the plausible-but-wrong) → Y triage real vs false → Y fold each real finding UPSTREAM into the
owning plan → A rebuild → G verify tree → M (who reviewed, what each found, verdicts)`.
*This is where the missing review manifest (issue #9) becomes the guaranteed output.*

**7. Review docs** (existing `doc-review`)
`A select doc-review personas → parallel review vs shipped truth → A drift check (docs vs code/gates) → Y fix →
G docs-drift + env-drift gates → M`.

**8. Verify / reproduce** (`verify`)
`A rebuild from pins → G assert byte-identical + 0 model calls → M (pin hits, any drift)`.
*Guard:* any non-pinned function is reported, not silently generated.

**9. Run gates / quality check** (`gate` / `lint-spec`)
`A run requested gates → G collect pass/fail → M (per-gate verdict)`. The lightest workflow; still records.

**10. Clarify a goal** (`clarify`)
`multi-interviewer front-end (thinking-scaled) → merge/dedupe questions → Y answer → A write testable
acceptance criteria → M (the brief + open questions)`.

**11. Author SDLC requirements** (existing `sdlc`)
`A analyst writes UC→BR→FR→TS (ID-traced) → G RTM gate (no orphans) → Y owner ratify → M`.

**12. Audit assumptions** (`assume`) — *promote from a step to a first-class workflow*
`A adversarial auditor → rank by materiality (fail-closed unknown→high) → Y/A resolve each (accept/pick/state
intent) → commit decisions.md → M`.

### Provenance / expert / lifecycle intents

**13. Trace / inspect** (`trace` / `metrics` / `status` / `whatis`)
`A gather → render provenance/metrics → M (or fold into the current run's manifest)`. Read-only; the record IS
the point.

**14. Select / grade experts** (`agent`) — *rebuild per issue #9*
`A usage-ledger read → grade-weighted select + explore/exploit → (rate: field-probe→judge→score) → M (who was
picked/graded, why)`.

**15. Onboard a new project** (existing `new-project`)
`Y/A intake → scaffold projects/<name> → author first plans → build-from-plan → G standing gates wired → M`.

**16. Ship / release** (`checkin`)
`G all gates green → G tree pristine → A cut canonical + tag → A push (LATHE_REMOTE) → M (what shipped, gate
evidence)`.
*Guard:* no release on a red gate or dirty tree.

**17. Maintain the tree** (`clean` / `checkpoint` / `dups`)
`A scan → quarantine corrupt/dup → G pristine + resource-dups gates → A checkpoint → M`.

**18. Serve the API** (`serve`)
`G refuse without token → G non-local bind requires docker → start → (each request re-enters the relevant
workflow above) → M (per request, via the same manifest)`.

**19. Report / triage issues** (`report` / `issues`)
`A file into shared queue → Y maintainer triage → (fix → bug-fix/enhancement workflow) → M`.

---

## Part 3 — Implementation split (what becomes code, skill, or data)

| Concern | Layer | Notes |
|---|---|---|
| The six-phase spine; step ordering; gate pass/fail enforcement; manifest emission | **deterministic code** (dispatcher/flow-runner) | non-bypassable; bare commands route through it |
| Which steps compose each invocation (Part 2) | **data** (`workflows.py`, extended) | auditable, editable, can't drift from hidden impl |
| Persona selection mechanics (grade-weight, explore/exploit) | **code** | deterministic given inputs (#9) |
| Persona bodies; analyst spec/test authoring; adversarial-case generation; review judgment | **skill + model** | gated: output must pass a check (tests kill mutants, gate goes green) |
| Thinking level → depth mapping | **code** | one dial onto tries/select/scrutiny |

**The litmus test again:** if skipping it should be *impossible*, it's code; if it needs a brain, it's a
skill whose output code gates.

---

## Part 4 — Rollout (after this design is ratified)

1. **Make the spine real:** the flow-runner becomes the implementation of the bare commands (promote `lathe
   flow` from opt-in to the default path); add always-on manifest emission (phase 5).
2. **Fill the data:** extend `workflows.py` from 6 to all 19 invocations per Part 2.
3. **Land the two feeders:** the review/build manifest (#9) and adversarial-test synthesis (#11) become the
   phase-4/phase-5 steps every invocation inherits.
4. **Verify by stress-test:** confirm no invocation can run around its contract, and every invocation emits a
   complete manifest — the same executable-probe method used on the gates.

*This is a design proposal for the maintainer, refined with the owner. The invocation taxonomy (Part 2) is a
starting set of 19 — ratify/adjust before implementation. Each workflow here is a first ideal draft; the
harness can brainstorm any one deeper (multi-perspective + adversarial synthesis) on request.*
