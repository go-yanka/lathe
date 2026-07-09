# Lathe

**A test-driven build engine for LLMs.** Treat AI code generation like a compiler, not a conversation: you
describe *what* you want as data (a plan) and its acceptance tests; a local model implements it under those
tests; passing code is content-hash **pinned** (so rebuilds are free and deterministic); and you **never
hand-edit generated code** — if it's wrong, you fix the spec and rebuild.

This is not an "autonomous AI engineer." It's a disciplined pipeline that makes AI-written code **tested,
reproducible, and clean** — and refuses anything that isn't.

## Why

Standard AI coding tools generate code you then tweak by hand — and the moment you do, you own the technical
debt and reproducibility is gone. Lathe forces every change *upstream into the spec*, keeps a **frontier model
for judgment** (writing specs + tests) and a **cheap local model for the typing** (implementing under those
tests), and gates the result. You get frontier-level judgment with local-level cost, speed, and privacy.

## How it works (30 seconds)

```
goal → ANALYST (frontier) writes spec + tests → IMPLEMENTER (local model) writes code
     → GATE runs the tests in an isolated sandbox → pass: PIN it / fail: rewrite the spec and retry
```

Full design + rationale: **[ARCHITECTURE.md](ARCHITECTURE.md)**. Threat model: **[SECURITY.md](SECURITY.md)**.

## Quick start

Requirements: Python 3.10+, an OpenAI-compatible local model endpoint (Ollama / llama-server / vLLM), and an
analyst endpoint (any OpenAI-compatible frontier model). Point Lathe at them with env vars:

```bash
export LOCAL_OPENAI_URL=http://localhost:8080/v1/chat/completions   # your local implementer
export HARNESS_CLAUDE_URL=http://localhost:8787/v1/chat/completions # your analyst (frontier)
export LATHE_MODEL=openai:local

python lathe.py selftest            # confirm the harness is healthy on your machine
python lathe.py do "a function that parses a duration like '2h30m' into seconds"
python lathe.py metrics summary     # build success rate, cost split, first-pass rate, churn
```

Reproducible demo (no model needed — proves the pinning story):

```bash
python lathe.py build examples/hello.py    # rebuilds a pinned, test-gated module deterministically, offline
```

Multi-plan demo (real composition — see [`examples/ledger/`](examples/ledger/)): three ordered plans build
`ledger_core` → `ledger_stats` → `ledger` (which composes them), each function gated. Then keep the tree
pristine locally *and* on your remote with the gated check-in:

```bash
python lathe.py checkin -m "my change" --push   # refuses unless gates green, no relics, not behind remote
```

## Workflows

Lathe ships named, transparent end-to-end **workflows** — so you (or an agent) can see exactly how a job is
handled *before* running it. `lathe flow` lists them; `lathe flow <name>` prints the ordered steps, each tagged
`[AUTO]` (a Lathe command), `[GATE]` (a tree check), or `[YOU]` (human judgment); `lathe flow <name> --run` runs
the automatable steps, halting on failure. Definitions are data in `projects/agentic-harness/tools/workflows.py`.

| Workflow | What it does |
|---|---|
| `code-review` | Multi-lens review of a change → land only *verified* fixes (upstream, in the plan). |
| `bug-fix` | Reproduce → diagnose from the run log → fix the **spec** → verify → review → release. |
| `enhancement` | Scope (vendor-don't-fork) → build **through** the harness → integrate → review → document → release. |
| `doc-review` | Coherence/accuracy review + the docs-drift gate (every command documented with an example). |
| `new-project` | Vendor Lathe → configure endpoints → verify → land the first gated build. |
| `sdlc` | **The full process, enforced**: RTM-gated requirements (UC→BR→FR→TS) → criteria-mapped plan → assumption audit → STRICT build → trace matrix → review. |

```
$ python lathe.py flow bug-fix        # show the steps
$ python lathe.py flow code-review --run   # execute the automatable steps
```

## Clarify before you build (the requirements liaison)

Most goals arrive underspecified — and an LLM handed an ambiguous goal produces *confidently wrong* code.
So Lathe can **interrogate you first**: `lathe clarify "<goal>"` runs a **requirements-liaison** persona that
asks the fewest, sharpest questions (inputs, outputs, success criteria, constraints, edge cases, non-goals),
takes your answers, and writes a `CLARIFIED_GOAL.md` brief with **testable acceptance criteria** — *before*
the harness designs anything. It's step 0 of the `sdlc` workflow; a clear goal is passed straight through.

Even without `clarify`, `lathe do` now **refuses to build on guessed material input**: when it can't ask
(no interactive terminal) it stops rather than assuming a default and building anyway — pass `--assume` to
build on documented defaults on the record. The short discovery interview that gathers those answers is run
**loudly** and can never be silently skipped.

## Expert agents on demand (the decider)

Lathe starts with **thinking**: a *decider* selects the right expert personas for the task before any code is
written. It's wired into the two thinking entry points — planning (`lathe do` injects goal-matched expert lenses)
and review (`lathe review auto <files>` auto-picks the domain-appropriate reviewer personas, e.g. security +
reliability for network code). Beyond the vendored personas, `lathe agent "<need>" --spawn` fetches expert agents
**on demand** from permissively-licensed open-source catalogs (license-gated, mirrored locally with their LICENSE)
— "load the program" for whatever capability a problem needs. All model-agnostic: a persona is just prompt text
injected into whatever endpoint you configured.

## A standing advocate (the sponsor's representative)

Beyond the reviewers, every `lathe do` runs a default-on **Advocate** — a persona that represents *your*
interest, not the code's. Seeded with your goal, the discovery answers, and the confirmed assumptions as a
**charter** (written to `ADVOCATE.md` in each workspace), it watches each step — discovery, assumptions,
delivery — carrying evolving memory across them, and judges **intent, direction, and quality** (not
correctness — the gates own that), returning APPROVE / CONCERN / VETO. A **VETO holds certification**: the
build prints `HELD`, not `DONE`, and exits nonzero, so a technically-green result that drifted from what you
asked for doesn't ship silently. Any Advocate outage is recorded as a CONCERN, never a silent pass. Off with
`LATHE_ADVOCATE=0`. *(Scope, honestly: it reviews intent at each step but does not yet vet the drafted
spec+tests **before** the build — that structural guardrail is pending.)*

## Ways to run it

Lathe talks to two OpenAI-compatible endpoints — an **analyst** (spec + tests) and an **implementer** (code) —
so it's model- and host-agnostic and drops into several setups:

- **Standalone tool** — drive it yourself: `lathe do "<goal>"` for a one-shot spec→build→pin, `lathe chat` for
  an interactive REPL, `lathe build <plan>` to rebuild a pinned module deterministically. Nothing else required.
- **Autonomous loop** — `lathe auto` drains a standing task board unattended, building and gating each item.
  Commits are opt-in (`LATHE_AUTO_COMMIT=1`) and off by default, so it never surprises your branch.
- **Inside an agent you already use (MCP)** — `lathe_mcp.py` is a stdio MCP server exposing
  `build / verify / gate / review / do` as tools, so Claude Code, Cursor, or Copilot get Lathe's hard test-gate,
  content-hash pinning, and provenance **beneath the agent**: the model proposes, Lathe gates and pins. A Claude
  **skill** (`skills/lathe/`) and a **plugin** manifest give one-step install.
  ```json
  { "mcpServers": { "lathe": { "command": "python", "args": ["lathe_mcp.py"] } } }
  ```
- **Driven by any OpenAI-compatible client** — point a desktop LLM client's custom-provider base URL at the
  bundled proxy (`claude_proxy.py`, serves `/v1`); the client drives builds through Lathe, and the proxy can back
  a role with a **Claude subscription at $0/token** (`claude login`, no API key) instead of a metered endpoint.

**Pick a model per role, mix freely:**

| Setup | Analyst (spec+tests) | Implementer (code) | Note |
|---|---|---|---|
| Local-first *(default)* | frontier, or subscription proxy | local model | cheapest; implementer runs on a small local model |
| All-subscription | Claude via `claude_proxy.py` | Claude fallback | $0/token, no API key |
| All-frontier | API model | API model | max quality, metered |
| Offline rebuild | — | — | pinned plans rebuild with **zero** model calls |

> **Independence, honestly:** rebuilds (pins) and *implementation* can run fully local; the **analyst still
> defaults to a frontier model**. A fully-local analyst is wireable (point both endpoints at local models) but
> not yet proven — so "no cloud at all" is a configuration, not yet a validated claim.

## What makes it trustworthy (not just fast)

- **Test comprehensiveness is measured, not assumed** — `lathe lint-spec`'s stub probe flags tests a
  trivial implementation could satisfy, and with `LATHE_MUTATION_SCORE=<0..1>` the engine generates
  deterministic AST mutants of the *accepted* code and **refuses to pin** unless the suite kills that
  fraction — a suite that can't tell `x*x` from `x+x` blocks the build (equivalent mutants are excluded so
  correct code is never falsely blocked; a bounded operator set, not exhaustive mutation coverage). (STRICT
  forces both.)
- **Isolated execution** — tests run in a sandbox with an unforgeable verdict; fully-untrusted plans run in a
  network-less, read-only container (locally or on a remote host over SSH). See `SECURITY.md`.
- **Ten standing gates** — no stale/duplicate files, one canonical implementation per capability, no corrupt
  files, no real-bug lint, docs can't drift. The tree stays pristine *intrinsically*, not via git.
- **Structured logging** — every run writes `runs/<id>.jsonl` (with secrets redacted); a bug report is
  self-diagnosing.
- **A change must prove itself** — with `LATHE_REGRESSION_PROOF=1`, a changed function (bug fix *or*
  enhancement) whose new tests all pass on the *old* accepted implementation is **refused before a single
  generation token is spent**: nothing demonstrates the new behavior, so a green rebuild would prove nothing.
- **Required test-kind per contract** — with `LATHE_TEST_KIND=1` (forced by STRICT), a function can declare
  the *kinds* of test it needs (`'kinds': ['property', 'edge']`); a unit whose tests lack a declared kind is
  **refused** — so an enhancement's invariant must ship a property test, not just an example.
- **Gate the glue** — with `LATHE_GATE_GLUE=1` (forced by STRICT), substantive hand-written `GLUE` wiring
  must be exercised by an `INTEGRATION` test or the build is **refused** — this is what lets the harness say
  *no code* ships untested, not just *no function*.
- **STRICT / SDLC mode** (`LATHE_STRICT=1`) — one switch forces every proof mechanism for **all**
  development: declared acceptance criteria (traceability), acknowledged tests, stub-proof tests for new
  code, failing-on-old-code proof for changed code, a mutation-score threshold, and the glue gate. The SDLC workflows build under it — the process is
  enforced, not advisory.
- **Requirement→test traceability, by construction** — a plan may declare acceptance criteria
  (`CRITERIA`); the validator **refuses** any criterion not mapped to a named, existing test, and
  `lathe trace` emits the criterion→test→pin→model matrix (which test proves which requirement, and which
  model wrote the accepted code). Scope stated honestly: enforced for *declared* criteria — declaring them
  is opt-in.
- **Honest metrics** — `lathe metrics summary` shows build success, cost, and churn. No hand-waving.

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — how it works and why
- [LATHE_COMMANDS.md](LATHE_COMMANDS.md) — every command with a runnable example
- [SECURITY.md](SECURITY.md) — the threat model and isolation tiers
- [DATA_QUALITY.md](DATA_QUALITY.md) — gating "unit-green but wrong on real data"
- [VENDORING.md](VENDORING.md) — one canonical copy; projects vendor, don't fork
- [CHANGELOG.md](CHANGELOG.md) — release notes (current: v2.61.0)
- [PERSONAS.md](PERSONAS.md) — the expert market: sources, the decider pipeline, ratings, your controls
- [REPRODUCIBILITY.md](REPRODUCIBILITY.md) — what's guaranteed (pinned rebuilds) vs what isn't (regeneration), measured
- [BENCHMARK.md](BENCHMARK.md) — an honest (warts-included) benchmark vs Aider/raw-Claude

## Status & honesty

Lathe is used internally to build real modules for real projects; it is disciplined and hardened, but it is
young. It depends on model endpoints you provide. Independent benchmarks vs. other tools are still to come. If
you try it, file issues — the feedback loop is part of the design.

## License

MIT — see [LICENSE](LICENSE).
