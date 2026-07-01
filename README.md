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

## What makes it trustworthy (not just fast)

- **Test-quality linter** (`lathe lint-spec`) — checks the tests are *good*, not just that they pass: a
  mutation probe flags a spec whose tests a trivial stub could satisfy.
- **Isolated execution** — tests run in a sandbox with an unforgeable verdict; fully-untrusted plans run in a
  network-less, read-only container (locally or on a remote host over SSH). See `SECURITY.md`.
- **Six standing gates** — no stale/duplicate files, one canonical implementation per capability, no corrupt
  files, no real-bug lint, docs can't drift. The tree stays pristine *intrinsically*, not via git.
- **Structured logging** — every run writes `runs/<id>.jsonl` (with secrets redacted); a bug report is
  self-diagnosing.
- **Honest metrics** — `lathe metrics summary` shows build success, cost, and churn. No hand-waving.

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — how it works and why
- [LATHE_COMMANDS.md](LATHE_COMMANDS.md) — every command with a runnable example
- [SECURITY.md](SECURITY.md) — the threat model and isolation tiers
- [DATA_QUALITY.md](DATA_QUALITY.md) — gating "unit-green but wrong on real data"
- [VENDORING.md](VENDORING.md) — one canonical copy; projects vendor, don't fork

## Status & honesty

Lathe is used internally to build real modules for real projects; it is disciplined and hardened, but it is
young. It depends on model endpoints you provide. Independent benchmarks vs. other tools are still to come. If
you try it, file issues — the feedback loop is part of the design.

## License

MIT — see [LICENSE](LICENSE).
