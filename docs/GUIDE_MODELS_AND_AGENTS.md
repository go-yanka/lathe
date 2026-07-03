# Guide — models & agents: plug in Hermes, GPT, Ollama, Claude Code, and more

*Lathe is **pluggable at both ends**. The **analyst** (writes spec + tests — the "thinker") and the
**implementer** (writes the code — the "builder") are independent endpoints you choose. This guide shows how
to wire common models and agents into each role.*

```
          ANALYST (thinker)                          IMPLEMENTER (builder)
   Claude subscription · any OpenAI-              local by default: Ollama · llama.cpp ·
   compatible endpoint · or a human      ──▶      vLLM · LM Studio (Hermes/Qwen/Llama/…) · or Claude
        writes spec + tests                            writes the code, under the gate
```

Related: `CLI_REFERENCE.md §3b` (every endpoint env var) · `GUIDE_CLAUDE_SUBSCRIPTION.md` · `GUIDE_MCP.md`.

---

## The two roles, and the vars that set them

| Role | What it does | Key env vars |
|---|---|---|
| **Analyst** | Writes the per-function spec + tests; runs `clarify`/`assume`/`review`. The "expensive brain," used sparingly. | `HARNESS_CLAUDE_URL` (endpoint), `HARNESS_ANALYST_MODEL` (model) |
| **Implementer** | Generates the code from the spec, gated + pinned. Cheap, local by default. | `LATHE_MODEL` (which model), `LOCAL_OPENAI_URL` **or** `OLLAMA_URL` (where) |

Set them per-command, in your shell, or in `lathe.config.json`. Full list + defaults: `lathe env`.

---

## Implementer recipes (the local "builder")

### Hermes / Qwen / Llama on an OpenAI-compatible server (llama.cpp, vLLM, LM Studio)

Any open model served over an OpenAI-compatible `/v1/chat/completions` endpoint works. Example — a Hermes
model on a local llama.cpp / vLLM server:

```bash
# start your server however you do (llama-server, vLLM, LM Studio) so it serves OpenAI-compatible on :8080
LATHE_MODEL=openai:local \
LOCAL_OPENAI_URL=http://127.0.0.1:8080/v1/chat/completions \
  lathe do "a function that parses '2h30m' into total seconds"
```

`openai:local` tells Lathe "use the OpenAI-compatible endpoint at `LOCAL_OPENAI_URL`." The model that
endpoint serves (Hermes, Qwen-Coder, Llama, Mistral, whatever you loaded) is the implementer. Tuning:
`LOCAL_OPENAI_MAXTOK` (default 16384), `LOCAL_GEN_TIMEOUT` (default 900s).

### Ollama (bare model name)

```bash
LATHE_MODEL=qwen2.5-coder \
OLLAMA_URL=http://localhost:11434 \
  lathe build plans/H_money.py
```

A bare model name (no `openai:` prefix) routes to Ollama at `OLLAMA_URL`.

### Best-of-N and the repair loop

The implementer is retried up to `LATHE_TRIES` times (default 3, the Rule-of-Three) — each attempt is gated,
and on failure the analyst sharpens the spec rather than escalating to a bigger model. A small local model in
this regime is the design's sweet spot.

---

## Analyst recipes (the "thinker")

### Your Claude subscription ($0/token)

The recommended default — see **`GUIDE_CLAUDE_SUBSCRIPTION.md`**. In short: run `claude_proxy.py`, point
`HARNESS_CLAUDE_URL` at it.

### GPT / Gemini / a local big model (any OpenAI-compatible endpoint)

```bash
# A non-local analyst host needs LATHE_TRUST_REMOTE_ANALYST=1 (the SSRF guard refuses remote hosts otherwise) —
# it's already in this block so the command runs as pasted:
LATHE_TRUST_REMOTE_ANALYST=1 \
HARNESS_CLAUDE_URL=https://api.openai.com/v1/chat/completions \
HARNESS_ANALYST_MODEL=gpt-4.1 \
  lathe do "a rate limiter with a token bucket"
```

Point it at OpenAI, an Azure deployment, OpenRouter, or a local 70B server — anything OpenAI-compatible. A
**local** analyst (e.g. `http://127.0.0.1:…`) needs no such flag; only non-local hosts do.

### No LLM analyst at all — you write the plans

A plan is a Python file: functions, each with a natural-language design and its tests. Write it by hand and
skip the analyst entirely; a local implementer fills in the code under the gate. See `LATHE_GUIDE.md §5` for
the plan format.

---

## Agent recipes (drive Lathe from a coding agent)

### Claude Code / Cursor / Copilot — via MCP

Register the MCP server and your agent gets `lathe_do` / `lathe_build` / `lathe_verify` / `lathe_gate` /
`lathe_review` as tools — Lathe becomes the build layer under the agent. Full setup:
**`GUIDE_MCP.md`**.

### Any shell-running agent — agent-native

An agent that can run shell commands can simply call the `lathe` CLI (`lathe do …`, `lathe build …`,
`lathe gate`) and read the results — use `lathe build --json` for a stable, parseable status line. No MCP
required; the CLI *is* the interface.

---

## Mix and match — a common setup

Claude subscription as the analyst (sharp specs, $0/token), a local Hermes/Qwen as the implementer (cheap,
private code gen), full rigor on:

```bash
# once (nohup so the proxy survives the shell closing; stop any old one first with pkill -f claude_proxy.py):
claude login && nohup python claude_proxy.py --port 8787 > claude_proxy.log 2>&1 &
# then, per build:
HARNESS_CLAUDE_URL=http://127.0.0.1:8787/v1/chat/completions HARNESS_ANALYST_MODEL=sonnet \
LATHE_MODEL=openai:local LOCAL_OPENAI_URL=http://127.0.0.1:8080/v1/chat/completions \
LATHE_STRICT=1 \
  lathe do "a function that validates an IBAN"
```

Big brain for judgment, small local model for volume, the gate for discipline — each swappable without
touching the others. Run `lathe env` any time to see every knob and its current value.
