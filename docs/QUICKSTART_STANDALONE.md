# Quickstart — run Lathe standalone

*The fastest path to a gated, pinned build on your own machine. Standalone is the **primary** way to run
Lathe: it's a single `lathe` command, stdlib-only (zero runtime dependencies), Python ≥3.10. Nothing here
talks to a cloud service you don't configure yourself.*

Related: `LATHE_GUIDE.md` (fuller install + plan format) · `CLI_REFERENCE.md` (every option) ·
`GUIDE_CLAUDE_SUBSCRIPTION.md` · `GUIDE_MODELS_AND_AGENTS.md` · `GUIDE_MCP.md`.

---

## 1. Install

```bash
# Option A — packaged (when published):
pipx install lathe-harness        # gives you a standalone `lathe` command

# Option B — from source (always works):
git clone <repo-url> && cd lathe
pip install -e .                  # installs the `lathe` entry point
#   …or skip install entirely and call:  python lathe.py <command>
```

The engine (`lathe.py`, `engine_v2.py`, `lathe_mcp.py`) is **stdlib-only** — no packages required to run the
core. Optional gates pull their own tools when you enable them (`ruff` for lint, `coverage`, `playwright`
for the functional gate).

Verify the install:

```bash
lathe help
lathe selftest        # confirms which capabilities are live on this machine
```

---

## 2. The three ways to run standalone

Lathe standalone has **degrees of "local"** — pick the one that fits what you have:

### a. Fully offline — rebuild from pins, zero model calls

If a plan is already built and its pins are committed, you can rebuild it with **no model and no network**:

```bash
lathe verify examples/hello.py     # replays the pins: byte-identical output, 0 model calls
lathe build  examples/hello.py     # reuses the pin — offline ONLY when every function is already pinned
```

This is the "the code was never the source, the spec was" demo. Nothing is generated; the pinned bytes are
replayed. Great for CI and air-gapped rebuilds. **Precondition:** `build` is offline *only when every
function in the plan is already pinned*. Run it on a fresh/unpinned plan and it will try to **generate** — and
error if no implementer is configured. Use `lathe verify` (or `build` on a committed, fully-pinned plan) for
the guaranteed-offline path.

### b. Standalone + a local model (the everyday mode)

Point Lathe's **implementer** at a local model, so generation stays on your machine:

```bash
# Ollama (bare model name):
LATHE_MODEL=qwen2.5-coder OLLAMA_URL=http://localhost:11434 \
  lathe do "a function that parses '2h30m' into total seconds"

# OR any OpenAI-compatible local server (llama.cpp / vLLM / LM Studio):
LATHE_MODEL=openai:local LOCAL_OPENAI_URL=http://127.0.0.1:8080/v1/chat/completions \
  lathe build plans/H_money.py
```

You still need an **analyst** (to write the spec + tests). Options: your Claude subscription
(`GUIDE_CLAUDE_SUBSCRIPTION.md`), any OpenAI-compatible endpoint (`GUIDE_MODELS_AND_AGENTS.md`), or write the
plan yourself (next).

### c. Standalone with **no LLM at all** — you write the plans

A plan is just a Python file describing functions + their tests. Write it by hand, and a local implementer
(or even best-of-N from a small model) fills in the code under the gate. See `LATHE_GUIDE.md §5` for the
plan format. If you also skip the implementer, you're back to mode (a): pin-replay only.

---

## 3. Your first build, end to end

```bash
# 1. One-shot from a goal (analyst specs it, local model builds it, gate verifies, it pins):
lathe do "a function that slugifies a title string"

# 2. Inspect what happened:
lathe metrics summary        # build success, tokens, tries
lathe plans                  # the plan files on disk
lathe trace <plan>           # criterion → test → pin → model  (the provenance record)

# 3. Prove reproducibility:
lathe verify <plan>          # rebuild from pins: byte-identical, 0 tokens
```

The rule that trips people up first and then becomes the thing they like: **you never hand-edit the
generated code.** Wrong behavior → sharpen the spec and rebuild.

---

## 4. Interactive shell (session mode)

For a back-and-forth session instead of one-shot commands:

```bash
lathe chat
lathe> a function that validates an email address    # a goal → it builds it
lathe> status                                        # any command works here too
lathe> build plans/H_money.py
lathe> quit
```

The REPL survives transient endpoint/board hiccups (prints the error, stays alive).

---

## 5. Turn on the discipline (optional but the point)

Everything above builds against the floor (tests must pass). To make the *rigor* non-optional:

```bash
LATHE_STRICT=1 lathe build plans/H_money.py
```

`LATHE_STRICT=1` composes the seven gates (traceability, regression-proof, mutation-score, test-ack,
test-kind, gate-the-glue, assumption gate). See `CLI_REFERENCE.md §3a` to arm them individually.

---

## 6. Where things live

| What | Where |
|---|---|
| Plans (your specs) | `plans/` (or wherever you point) |
| Pins (reproducibility cache) | `.pins.json` next to the built module |
| Run logs | `<harness>/runs/` (`LATHE_LOG_DIR`) |
| Metrics ledger | `<root>/metrics/runs.jsonl` (`LATHE_METRICS_PATH`) |
| Config (optional) | `./lathe.config.json` or `~/.lathe/config.json` (`LATHE_CONFIG`) |

Standalone Lathe keeps your source, specs, and pins on your machine. Nothing leaves it except the model
calls to the endpoints **you** configure — and in mode (a), not even those.
