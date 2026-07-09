# Lathe — How It Works, and Why

Lathe is a **test-driven build engine for LLMs**. The one-line thesis: *treat AI code generation like a
compiler, not a chat.* You describe **what** you want as data (a plan) and its acceptance tests; the harness
produces **tested, reproducible** code and refuses anything that doesn't pass. You never hand-edit the output —
if it's wrong, you fix the spec and rebuild.

## The core loop

```
        ┌─────────────┐   spec + tests    ┌──────────────┐   code    ┌─────────────┐
  goal ─▶│  ANALYST    │──────────────────▶│  IMPLEMENTER │──────────▶│    GATE     │
        │ (frontier /  │                   │ (local model / │           │ tests run in│
        │  Claude)     │◀──────────────────│  the rig)    │           │ a SANDBOX   │
        └─────────────┘   repair: rewrite  └──────────────┘           └──────┬──────┘
              ▲            the spec from the                                  │
              │            exact failing test                     pass │      │ fail
              │                                                         ▼      ▼
              └──────────────────────────────────────────────  PIN (content hash)  ──▶ next
                                                                (rebuilds are free + deterministic)
```

1. **Analyst** (a frontier model) does the *thinking*: it writes the function specs **and the tests** that
   define "correct." It never writes the implementation.
2. **Implementer** (a cheap local model on the rig) does the *typing*: it writes code to pass those tests.
   High-frequency, low-cost iteration happens here.
3. **Gate**: each function's tests run in an isolated sandbox. Pass → the implementation is **pinned** by a
   content hash (rebuilds reuse it instantly, for free, deterministically). Fail → the **repair loop** feeds
   the exact failing test back to the analyst, which *rewrites the spec* and tries again.

## Why this shape (the bets)

- **Two-tier (frontier spec / local implement).** The durable win isn't just cost — it's **latency and
  burst**: a test-driven loop hammers the model with many quick iterations, and a local rig gives zero-rate-
  limit, zero-network-latency capacity for that. The frontier model is reserved for judgment (specs, review).
- **Never hand-edit generated code.** The moment a human tweaks the output, the human owns the technical debt
  and reproducibility is lost. Lathe forces every change *upstream* into the spec, so the AI owns the code and
  the build stays reproducible.
- **Plans are DATA, executed by the engine.** A plan is a Python literal (`OUT_DIR`, `MODULE_NAME`,
  `FUNCTIONS=[{name, prompt, tests}]`, optional `HEADER`/`GLUE`/`ARTIFACTS`/`INTEGRATION`/`PRELUDE`/`RETIRE`).
  This is Makefile-like — and the central attack surface, which is why it's locked down (below).

## The safety spine (why it's trustworthy)

- **Plan validator** (`plan_validator.py`) — a *closed-rule* gate: import allowlist, literal-only executed
  values, no dunder access, identifier-only names, ≥1 test per function. A malformed or prompt-injected plan is
  refused *before* anything runs. (Hand-maintained security infra; the engine refuses to regenerate it.)
- **Sandbox** (`sandbox.py`) — tests run in an isolated subprocess with an **unforgeable verdict**: the parent
  hands the child a secret nonce over stdin, the child's stdout is redirected to devnull, and only a
  nonce-framed line is believed — so a malicious test can't print a fake "pass." For fully untrusted plans,
  `docker` / `docker-ssh` mode runs it in a throwaway, network-less, read-only container (on the rig over SSH
  when local docker is absent). See `SECURITY.md`.
- **Test-quality linter** (`spec_lint.py`) — the gate checks tests *pass*; this checks they're *good*. A
  **mutation probe** runs trivial stub impls (`return None`/`0`/identity) against the tests; if a stub passes
  them all, the tests don't pin behavior and the spec is flagged (or blocked). Closes the "green build, wrong
  code" gap.
- **Spec↔test consistency** (`LATHE_SPEC_TEST_STRICT`, default **on** in `engine_v2`) — if the drafted spec
  and its tests contradict each other and the contradiction is left unreconciled, the build is **refused**
  rather than silently resolving it one way.
- **Cleanliness gates** (`qa/run_gates.py`, run every build) — the tree must stay pristine *intrinsically*, not
  via git: no stale/backup/duplicate files, one canonical DB, one `live` implementation per capability
  (registry), no corrupt files, no real-bug lint, every CLI command documented (docs-drift), and every env var
  the code reads documented in `env_catalog.py` / `lathe env` (env-drift). Divergence is a **build failure**,
  not a latent trap.

## The enforcement layer (methodology, not just a test-gate)

Beyond "code must pass its tests," a stack of **opt-in gates** makes the *kind and comprehensiveness* of
testing a property of the process, not the model's discretion. Each is harness-built (a pinned pure function
in `tools/`) with its own acceptance test in `review_tests/`, and `LATHE_STRICT=1` composes all of them:

1. **Traceability** (`CRITERIA` + `lathe trace`) — a plan's declared acceptance criteria must each map to a
   named, existing test, or the validator refuses it; `lathe trace` emits the criterion→test→pin→model matrix.
2. **Regression-proof** (`LATHE_REGRESSION_PROOF=1`) — a *changed* function (fix or enhancement) whose new
   tests all pass on the old accepted code is refused: a change must ship a test that proves the new behavior.
3. **Mutation-score** (`LATHE_MUTATION_SCORE=<0..1>`) — deterministic AST mutants of the accepted code must be
   killed by the suite before it may pin; provably-equivalent mutants are excluded (no false blocks). A bounded
   tripwire for vacuous tests, honestly *not* exhaustive mutation coverage.
4. **Test-ack** (`LATHE_TEST_ACK=1`, `lathe ack`) — the analyst's tests define truth, so a human acknowledges
   the exact test set (keyed by digest) before the build certifies it; any rewrite re-forces it.
5. **Test-kind** (`LATHE_TEST_KIND=1`) — a function can require the *shape* of test it needs
   (`'kinds': ['property','edge']`); a unit missing a declared kind is refused. Honest caveat: kind detection
   is a **substring heuristic** over the test text — a comment or string literal can satisfy a required kind
   without a real assertion, so this catches *absence* of a kind, not its *quality*; the mutation-score gate
   is the real backstop against vacuous tests.
6. **Gate-the-glue** (`LATHE_GATE_GLUE=1`) — hand-written `GLUE` wiring must be exercised by an `INTEGRATION`
   test or the module is refused — so *no code* ships untested, not just no function.
7. **Assumption gate** (`LATHE_ASSUMPTION_GATE=1`, `lathe assume`) — an underspecified goal makes the model
   fill gaps with silent guesses ("intent drift"), and when told to ask it rates its own guesses as "common
   enough" and proceeds. So an *adversarial* `assumption-auditor` persona re-reads the spec against the goal,
   emits a materiality-ranked ledger of the choices the goal never specified, and the build **refuses to
   proceed while any blocking-materiality assumption is unresolved**. `lathe assume <plan> --resolve` throws
   each one back for an explicit, per-item decision (accept as-is / pick an offered alternative / state your
   own intent) — recorded in a committed `<plan>.decisions.md`, so a resolved assumption becomes a stated
   decision, not a silent guess. Nothing is auto-accepted (bulk accept is an explicit `--accept-all` opt-in,
   logged as such). Scrutiny is user-governed (`all|high+med|high|off`); resolutions are keyed to a spec
   digest, so any spec change re-opens the audit. Runs advisory at `clarify`, enforced pre-build. A tripwire
   against silent intent-drift, not a proof of full intent capture.

## Thinking first: clarify → decide → build

- **Goal intake in `lathe do`** (`cmd_do` → `_goal_intake`) — every `do` now runs a live intake *before*
  drafting: STAGE 0 **DISCOVERY** (a `requirements-liaison` persona interrogates the goal's real intent) →
  **ASSUMPTIONS** (an `assumption-auditor` persona surfaces the unstated choices, now de-duplicated in
  `assumption_logic.py`) → interactive **CONFIRM** → draft spec. If material assumptions stay unconfirmed and
  there is no interactive terminal, the build is **refused** (`IntakeAbort`) instead of auto-accepting the
  guesses. (Discovery was previously dead code — a swallowed `NameError` — and is now functional and loud.)
- **Requirements liaison** (`lathe clarify`) — before any design, a liaison persona *interrogates the user*
  to remove ambiguity (inputs, outputs, success criteria, constraints, edge cases, non-goals) and writes a
  `CLARIFIED_GOAL.md` brief with testable acceptance criteria. It's step 0 of the `sdlc` workflow.
- **The decider / persona market** — a *decider* selects expert personas before code is written: a catalog of
  143 (12 vendored Compound-Engineering reviewers + 129 permissive fetch-on-demand), matched by
  synonym/stemming, reweighted by **measured ratings** (`lathe agent rate`) and your config
  (`personas.priority`/`mandatory`), with a guaranteed **CE-reviewer floor** in every call. Absent experts are
  fetched license-gated and their body injected. See `PERSONAS.md`.
- **SDLC authoring** (`lathe sdlc`) — the analyst writes layered, ID-traced requirements (UC→BR→FR→TS) and an
  RTM gate refuses orphans/dangling refs, emitting `REQUIREMENTS.md` + a criteria-mapped plan.

## The Advocate — the sponsor's standing proxy

Default-on (`LATHE_ADVOCATE`), the **Advocate** (`ce_personas/advocate.md` + `tools/advocate.py`) is a single
standing persona that represents the sponsor across the *whole* run — not a per-file reviewer. In `lathe do`
it is seeded with a **CHARTER** (the goal + discovery answers + confirmed assumptions, written to `ADVOCATE.md`
in the workspace) and runs checkpoints at **DISCOVERY**, **ASSUMPTIONS**, and **DELIVERY**, each logged to
`ADVOCATE_LOG.md` with evolving memory carried between them. It judges *intent, direction, and quality* — not
code correctness — and returns **APPROVE / CONCERN / VETO** (a VETO carries a route:
`rediscover | reassume | redraft | rebuild`). A VETO **holds** the run: it prints `HELD`, not `DONE`, and exits
nonzero. It is enforced as a standing gate (`qa/advocate_gate.py`, registered in `qa/run_gates.py`). Fail-safe
by design: an Advocate outage degrades to **CONCERN**, never a silent pass or a crash. Tunables:
`LATHE_ADVOCATE_MODEL`, `LATHE_ADVOCATE_TIMEOUT`. *Known-open: the Advocate does not yet checkpoint the drafted
SPEC+TESTS before the build — that guardrail is pending.*

## Autonomy

A SQLite **board** (kanban) + a **DAG** of dependencies + a **planner** (asks the analyst for the next spec
when the board empties) + a **dispatcher** (`lathe run`) drive many tasks to gated-green unattended. Long jobs
can go **dormant** awaiting a signal (`lathe wait/resume`) and resume from durable state. Every run writes a
structured log (`runs/<id>.jsonl`) and a metrics row, so an unattended run is fully auditable after the fact.

## Reproducibility & distribution

Pins make an unchanged plan rebuild instantly and identically. One **canonical** copy holds all hardening;
consuming projects **vendor** a pinned, tested copy (they don't fork), and general improvements flow back.
Cleanliness, security, and test-quality are all enforced *in the tree*, not assumed — which is the whole point:
**you can trust the output because the process refused everything that wasn't verified.**
