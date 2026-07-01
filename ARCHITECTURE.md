# Lathe — How It Works, and Why

Lathe is a **test-driven build engine for LLMs**. The one-line thesis: *treat AI code generation like a
compiler, not a chat.* You describe **what** you want as data (a plan) and its acceptance tests; the harness
produces **tested, reproducible** code and refuses anything that doesn't pass. You never hand-edit the output —
if it's wrong, you fix the spec and rebuild.

## The core loop

```
        ┌─────────────┐   spec + tests    ┌──────────────┐   code    ┌─────────────┐
  goal ─▶│  ANALYST    │──────────────────▶│  IMPLEMENTER │──────────▶│    GATE     │
        │ (frontier /  │                   │ (local 35B / │           │ tests run in│
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
- **Cleanliness gates** (`qa/run_gates.py`, run every build) — the tree must stay pristine *intrinsically*, not
  via git: no stale/backup/duplicate files, one canonical DB, one `live` implementation per capability
  (registry), no corrupt files, no real-bug lint. Divergence is a **build failure**, not a latent trap.

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
