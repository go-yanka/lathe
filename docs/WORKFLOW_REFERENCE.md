# Lathe — Workflow Reference (Fable edition)

*The core "how Lathe actually works" manual: every workflow, how you invoke it, what it does and how, which
gates fire, which personas are involved, what you can tune, and what you get at the end — step by step.
Authored directly from the source (`workflows.py`, `lathe.py`'s spine, the gate code) at **v2.18.0**. A
companion machine-generated edition (`WORKFLOW_REFERENCE_HARNESS.md`) and a diff (`WORKFLOW_REFERENCE_
COMPARISON.md`) accompany this. **Note:** this describes what each workflow *claims* to do; a step-by-step
live test pass is a separate, deliberate follow-up.*

---

## 0. The two things you need to understand first

### 0.1 What a "workflow" is
A workflow is an **ordered, named series of steps** for one job (fix a bug, review a change, build from a
goal…). Definitions are **data** (`tools/workflows.py`), not hidden code, so they can't drift from a secret
implementation and you can read exactly what will happen before you run it. Each step has a **kind**:

| Kind | Meaning | Runs automatically? |
|---|---|---|
| **AUTO** | a real `lathe` subcommand, gated on success (a non-zero exit halts the workflow) | yes (`--run`) |
| **GATE** | a standing check (`lathe gate`) that must pass | yes (`--run`) |
| **YOU** | a human/analyst judgment checkpoint (printed, never auto-run) | no — you do it |

### 0.2 Two ways every workflow reaches you
1. **Explicit:** `lathe flow <name>` prints the workflow's contract + steps (a *dry* view); `lathe flow
   <name> --run <targets>` executes the AUTO/GATE steps in order, halting on the first failure.
2. **Promoted (the operating contract):** as of the Phase-2 promotion, a **bare command routes *through* its
   workflow**. `lathe do`, `lathe build`, `lathe review`, `lathe sdlc`, etc. each map (via `CONTRACT_FOR`) to
   a workflow and run through the **six-phase spine**: `intake → front-end → selection → work → gate →
   manifest`. Every invocation emits a per-run **manifest** to `docs/ce/<run_id>.manifest.json` (the audit
   record), un-skippable. A command not in `CONTRACT_FOR` (e.g. `status`, `logs`) is *trivial*: the spine
   still runs + emits a manifest, but the enforcement phases no-op.

### 0.3 The dials that apply to (almost) every workflow
| Dial | What it does | Default |
|---|---|---|
| `LATHE_THINK` = `casual`/`medium`/`high` | scales depth: personas employed, best-of-N (`LATHE_TRIES`), assumption scrutiny, adversarial effort | `medium` |
| `LATHE_STRICT=1` | composes the 7 build-time rigor gates (traceability, regression-proof, spec-lint, mutation-score, test-ack, test-kind, gate-the-glue, assumption) | off (but the `bug-fix`/`enhancement`/`sdlc` workflows turn it on in their build step) |
| `LATHE_PERSONA_UCB` | UCB1 explore/exploit persona selection (default on since v2.16.0) | on |
| `LATHE_SPINE=off` | bypass the contract (recorded in the manifest as `disabled-by-operator`) | on |
| gate env vars | tune individual gates (`LATHE_MUTATION_SCORE`, `LATHE_GLUE_MAX`, `LATHE_ASSUMPTION_POLICY`, …) — see `GATES_REFERENCE.md` / `TUNING.md` | per-gate |

**The standing gate suite** referenced by every GATE step is the 10 tree gates run by `qa/run_gates.py`:
`stale · resource-dups · registry · pristine · real-bug-lint · docs-drift · env-drift · manifest-contract ·
spine-enforced · gate-tristate`. Full detail: `GATES_REFERENCE.md`.

---

## Part 1 — The six named, end-to-end workflows

These are the multi-step workflows you invoke by name (`lathe flow <name> --run`). Each carries an up-front
**contract** (when/entry/deliverable/done).

### 1.1 `code-review` — land only verified fixes
- **Invoke:** `lathe flow code-review --run <files>`  ·  (bare `lathe review <files>` runs the review step
  under the spine).
- **When:** a change is ready and you want *only verified* fixes landed. **Entry:** the changed files build;
  you know which plan owns them. **Deliverable:** real findings folded UPSTREAM into the owning plans, rebuilt
  + gated — nothing hand-edited. **Done:** gates green, touched specs pass `lint-spec`, canonical re-cut.
- **Steps:**
  1. **AUTO** `review auto {files}` — the **persona decider** picks reviewer personas for the code's domain
     (UCB1 over the graded/usage ledger) and runs the multi-lens review (correctness + adversarial floor,
     plus domain lenses). *Expect:* findings printed + a manifest recording who reviewed and what they found.
  2. **GATE** — cleanliness / lint / docs-drift standing gates. *Expect:* pass, or a specific gate failure.
  3. **YOU** — triage real findings vs false positives; write the fix for each real one.
  4. **YOU** — fix **upstream**: fold each real finding into the owning plan and `lathe build <plan>` — never
     hand-edit generated code.
  5. **YOU** — if this was a shipped fix, re-cut canonical (release immediately).
- **Personas:** dynamic, chosen by the decider (security/perf/concurrency/… per the code). **Gates:** the
  standing suite (step 2) + the rigor gates on any rebuild (step 4). **Tune:** `LATHE_THINK` (how many
  personas), the lens set. **End state:** reviewed change, findings folded to specs, gated rebuild.

### 1.2 `bug-fix` — correct it at the source, not patched
- **Invoke:** `lathe flow bug-fix --run <plan> <files>`.
- **When:** a build/behavior is wrong and you need it fixed at the source. **Entry:** you can name + reproduce
  the failing plan. **Deliverable:** spec/tests pin the correct behavior, a green rebuild, the fix reviewed.
- **Steps:**
  1. **AUTO** `build {plan}` — reproduce; captures a run log. 2. **AUTO** `logs --tail` — read the full trace
  (every model call + verdicts): spec bug or impl bug? 3. **AUTO** `lint-spec {plan}` — are the tests even
  good (can a trivial stub pass them)? 4. **YOU** — fix the SPEC/tests to pin correct behavior, then rebuild.
  5. **AUTO** `assume {plan}` — assumption audit (HIGH-materiality blocks). 6. **AUTO** `build {plan}` under
  **STRICT** — the fix must ship a test that **fails on the old code** (regression-proof). 7. **GATE** — tree
  clean + no regression. 8. **AUTO** `review auto {files}` — decider reviews the fix. 9. **YOU** — resolve the
  issue + re-cut canonical.
- **Gates:** spec-lint (3), assumption (5), the 7 STRICT rigor gates incl. **regression-proof** (6), standing
  suite (7). **Personas:** decider's pick (8). **Tune:** `LATHE_STRICT` (forced on in step 6),
  `LATHE_ASSUMPTION_POLICY`. **End state:** a bug that can't silently come back (a reproducing test is now
  pinned).

### 1.3 `enhancement` — a new capability, built the disciplined way
- **Invoke:** `lathe flow enhancement --run <plan> <files>`.
- **When:** you want a NEW capability, dogfship through the harness. **Entry:** scoped as harness-framework vs
  project-specific (the vendoring boundary). **Deliverable:** small pure functions + strong tests, built by
  the harness, reviewed, documented.
- **Steps:** 1. **YOU** scope (harness vs project — vendor-don't-fork). 2. **YOU** design pure functions +
  declare required test **kinds** per function (`'kinds': ['property','edge']`). 3. **AUTO** `assume {plan}`.
  4. **AUTO** `build {plan}` under STRICT. 5. **AUTO** `lint-spec {plan}`. 6. **GATE** integrate + verify the
  tree. 7. **AUTO** `review all {files}` (all lenses). 8. **YOU** document it with an example (the docs-drift
  gate enforces this). 9. **YOU** re-cut canonical.
- **Gates:** assumption (3), STRICT incl. **test-kind** (4), spec-lint (5), standing suite (6), **docs-drift**
  (enforced by step 8's requirement). **Personas:** all lenses (7). **End state:** a gated, tested,
  reviewed, documented capability.

### 1.4 `doc-review` — prove the docs haven't drifted from the code
- **Invoke:** `lathe flow doc-review --run <files>`.
- **When:** docs/plans need an accuracy check + proof of no-drift. **Deliverable:** a coherence/accuracy
  review + a passing docs-drift gate.
- **Steps:** 1. **AUTO** `review maintainability {files}` — the doc-review lens. 2. **GATE** docs-drift —
  every CLI command documented with an example, or the build fails. 3. **YOU** fix gaps; keep every example
  runnable.
- **End state:** docs verified coherent + the drift gate green.

### 1.5 `sdlc` — the full process, enforced end to end
- **Invoke:** `lathe flow sdlc --run <goal> <plan> <files>` (needs analyst + implementer endpoints).
- **When:** you want the FULL process: ID'd requirements, traceability, every proof gate. **Deliverable:**
  RTM-gated `REQUIREMENTS.md` + a criteria-mapped plan built under STRICT + the trace matrix.
- **Steps:** 1. **AUTO** `clarify {goal}` — the requirements liaison interviews you first. 2. **AUTO**
  `sdlc {goal}` — author layered UC→BR→FR→TS requirements; the **RTM gate** refuses orphans/dangling refs.
  3. **YOU** turn the CRITERIA block into a plan. 4. **AUTO** `ack {plan}` — acknowledge the test set.
  5. **AUTO** `assume {plan}` — every HIGH assumption must be decided. 6. **YOU** `assume {plan} --resolve`
  each blocker (accept / pick / state intent → `<plan>.decisions.md`). 7. **AUTO** `build {plan}` STRICT.
  8. **AUTO** `trace {plan}` — emit the requirement→test→pin→model matrix (the compliance artifact).
  9. **AUTO** `review auto {files}`. 10. **GATE** tree clean. 11. **YOU** release.
- **Gates:** RTM/traceability (2), test-ack (4), assumption (5–6), all 7 STRICT rigor gates (7), standing
  suite (10). **End state:** a fully-traced, provably-gated feature with a compliance matrix.

### 1.6 `new-project` (alias `onboard-project`) — vendor Lathe into a repo
- **Invoke:** `lathe flow new-project --run`.
- **When:** onboarding a fresh project. **Deliverable:** a vendored, configured, verified install + a first
  gated build landed.
- **Steps:** 1. **YOU** vendor a pinned copy (keep your product layer separate). 2. **YOU** configure
  `LOCAL_OPENAI_URL` (implementer) + `HARNESS_CLAUDE_URL` (analyst). 3. **AUTO** `selftest`. 4. **GATE** tree
  clean. 5. **AUTO** `do "a small pure helper"` — first build, gated + pinned. 6. **YOU** add your product's
  data-quality gates.
- **End state:** a working Lathe install with one pinned build.

---

## Part 2 — The per-invocation workflows (bare commands, promoted through the spine)

These are what a **bare command** runs when the operating contract promotes it. Each is primitive-first
(`{args}` passthrough, so stdout + exit code are preserved) plus only the steps that *add* enforcement, and
each emits a manifest. `CONTRACT_FOR` records the command's flags — `front_end` (clarify/assume), `select`
(personas), `gate` (phase-4 standing gates), `writes` (mutates the tree).

| Command | Workflow | Steps (beyond the primitive) | front/select/gate/writes | End artifact |
|---|---|---|---|---|
| `lathe do <goal>` | build-from-goal | + standing gate + read-manifest | 1 / 1 / 0¹ / 1 | pinned build + manifest |
| `lathe build <plan>` | build-from-plan | + `trace {plan}` + read-manifest | 0 / 0 / 0¹ / 1 | pinned build + trace + manifest |
| `lathe sdlc <goal>` | sdlc-requirements | + review REQUIREMENTS.md | 1 / 1 / 1 / 1 | RTM-gated requirements |
| `lathe clarify <goal>` | clarify-goal | (single: interview → brief) | 1 / – / – / 1 | `CLARIFIED_GOAL.md` |
| `lathe assume <plan>` | assumption-audit | (single: audit → decisions) | – / – / 1 / 1 | ranked ledger + `decisions.md` |
| `lathe verify <plan>` | verify-reproduce | (single: replay pins) | – / – / 0 / 0 | byte-identity proof |
| `lathe trace <plan>` | trace-inspect | (single: matrix) | – / – / – / 0 | traceability matrix |
| `lathe gate` | (trivial²) | run the standing suite | – / – / – / 0 | exit-honest gate report |
| `lathe clean` | maintain-tree | janitor + standing gate | – / – / – / 1 | pristine tree |
| `lathe checkin` | ship-release | leak-scan check-in + YOU tag | – / – / – / 1 | committed, tagged release |
| `lathe serve` | serve-api | serve the REST API | – / – / – / 0 | running API |
| `lathe agent <need>` | select-grade-experts | match/spawn persona(s) | – / – / – / 0 | fetched persona body |
| `lathe report <title>` | report-triage | collect + YOU triage | – / – / – / 0 | filed/triaged issue |
| `lathe auto <objective>` | autonomous | the supervised autonomy loop | – / – / – / 1 | gated commits (opt-in) |

¹ `gate:0` on `do`/`build` is deliberate — the **engine already runs the standing regression inside the
build**, so a phase-4 gate would double-cost for zero coverage. ² `gate` is itself the gate run; repeating it
in phase-4 adds nothing.

**Tuning the per-invocation workflows:** the same dials — `LATHE_THINK` (depth), `LATHE_STRICT` (rigor on a
build), `LATHE_ASSUMPTION_POLICY` (how aggressively `assume` blocks), `LATHE_AUTO_COMMIT` (whether `auto`
commits), the REST vars (`LATHE_API_TOKEN`/`LATHE_API_PORT`) for `serve`. See `TUNING.md`.

---

## Part 3 — What you get at the end of *any* workflow

Every promoted invocation writes **`docs/ce/<run_id>.manifest.json`** (+ a `.md` render): the goal, the
workflow resolved, the personas/lenses selected and why, each contributor and what it found, the gate
verdicts, the thinking level, models, tokens/cost, timing, and the pass/refuse/error outcome. Builds
additionally write **pins** (`.pins.json`) for byte-identical rebuilds; `sdlc`/`trace` write the
**traceability matrix**; `assume` writes **`<plan>.decisions.md`**; `clarify` writes **`CLARIFIED_GOAL.md`**.
The manifest is the single artifact that lets you eyeball exactly what the harness did.

---

## Part 4 — Known caveats (from the v2.16.0 capstone, mostly fixed in v2.17–2.18)

Recorded here for honesty and to focus the upcoming live-test pass:
- The CLI-regression class (`review auto`/`review <lens>`/`build <stem>` mis-binding) was **fixed in v2.17**.
- Persona **grades** and the live decider wiring were fixed in v2.17–2.18 (UCB1 now default-on; grades now
  computed). The `select`/`front_end` contract flags were reported **decorative** (only `workflow`/`gate`
  read by the spine) — **to be re-confirmed in the live test pass**, since a workflow whose steps don't
  actually include a clarify/assume/persona step won't perform it just because the flag is set.

*This is the claimed behavior, read from the source. The next activity — a one-by-one live test of each
workflow — verifies whether each does what it says here.*
