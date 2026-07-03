# Guide — use your Claude *subscription* as the analyst (no API key)

*Lathe's **analyst** (the model that writes the spec + tests) can run on your existing Claude subscription —
the same `claude login` you use for Claude Code — at **$0 per token**, no API key, no separate billing. The
bridge is a small proxy that ships with the repo: `claude_proxy.py`.*

> This is about the **subscription**, not the Anthropic **API**. If you have an API key instead, point
> `HARNESS_CLAUDE_URL` straight at Anthropic (or any OpenAI-compatible gateway) — see
> `GUIDE_MODELS_AND_AGENTS.md`. This guide is for the "I pay for Claude, not per token" case.

Related: `QUICKSTART_STANDALONE.md` · `CLI_REFERENCE.md §3b` (endpoint env vars) · `LATHE_GUIDE.md §7a`.

---

## What it is

`claude_proxy.py` is *"a minimal OpenAI-compatible proxy that wraps the Claude Code CLI."* Every analyst
request Lathe makes is turned into a local HTTP call; the proxy shells out to `claude -p …`, which
authenticates through **your** Claude subscription (`claude login`). Lathe never sees a key, and there is
**zero per-token cost** — you're using the plan you already pay for.

```
Lathe (analyst request)  ──HTTP──▶  claude_proxy.py :8787  ──shells──▶  claude -p  ──▶  your Claude subscription
```

The **implementer** (the model that writes the code) is separate and stays local — see
`GUIDE_MODELS_AND_AGENTS.md`. This guide only wires up the *analyst*.

---

## Setup — three steps

```bash
# 1. Log in to Claude once (the same login Claude Code uses):
claude login

# 2. Start the proxy (leave it running; default port 8787).
#    Use nohup (or tmux/systemd) so it survives the terminal closing — a bare `&` dies when the shell exits,
#    and re-running it double-binds :8787 (the "address already in use" error is swallowed by `&`).
#    Stop any old instance first:  pkill -f claude_proxy.py
nohup python claude_proxy.py --port 8787 > claude_proxy.log 2>&1 &

# 3. Point Lathe's analyst at it:
export HARNESS_CLAUDE_URL=http://127.0.0.1:8787/v1/chat/completions
export HARNESS_ANALYST_MODEL=sonnet        # or opus / haiku — whichever your plan allows
```

That's it. Now any command that needs the analyst uses your subscription:

```bash
lathe clarify "a money parser"          # analyst asks the clarifying questions
lathe do "parse '2h30m' into seconds"   # analyst writes the spec+tests; your implementer builds it
lathe assume plans/H_money.py           # the adversarial auditor runs on your subscription
```

Persist it instead of exporting each session by putting it in `lathe.config.json`:

```json
{ "analyst": { "url": "http://127.0.0.1:8787/v1/chat/completions", "model": "sonnet" } }
```

**Footgun to know:** an explicit env var **silently wins** over the config file. If you set the proxy in
`lathe.config.json` but a stale `HARNESS_CLAUDE_URL` is still exported in your shell profile, the analyst
quietly routes *there* instead — you never touch the subscription you configured. Run **`lathe env`** to see
the *effective* endpoint and whether it came from env or the file; `unset HARNESS_CLAUDE_URL` if you want the
config file to win.

---

## Good to know

- **Vision (what actually works).** `claude -p` is text-in, so the proxy handles images by saving them to a
  local file for Claude Code's Read tool. Concretely (per `claude_proxy.py`): standard OpenAI `image_url`
  blocks with an **inline `data:` (base64) image are supported** — PNG/WebP/JPG are decoded to a temp file
  and read. **Remote `http(s)` image URLs are *not* fetched** (Claude Code reads files, not the web), so send
  images inline as base64, not as links.
- **Resilience.** If the proxy or the CLI hiccups mid-run, Lathe's `chat` REPL and repair loop print the
  error and keep going rather than crashing.
- **Cost.** The analyst is the "expensive brain," used only for spec/review — not the bulk implementer. On a
  subscription that's $0/token; the code generation happens on your local implementer.

---

## ⚠️ The one rule that matters (compliance)

**Anthropic prohibits routing *other people* through a single subscription.** `claude_proxy.py` is for
**your own solo / internal use** — you, on your machine, using your plan. Do **not** stand it up as a shared
service that fans multiple users' requests through one subscription; that violates Anthropic's terms. For
multi-user or production, use API-key auth (point `HARNESS_CLAUDE_URL` at Anthropic or your gateway) instead.
See `COMPLIANCE.md` in the repo for the full statement.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `analyst proxy reachable` fails in `lathe selftest` | The proxy isn't running or the URL is wrong. Start `python claude_proxy.py --port 8787` and re-check `HARNESS_CLAUDE_URL`. |
| Auth errors from `claude -p` | Run `claude login` again; confirm the CLI works standalone: `claude -p "say ok"`. |
| Analyst calls time out on big specs | Raise `CLAUDE_TIMEOUT` (default 600s) and/or `CLAUDE_RETRIES` (default 2). |
| Want a different Claude model | Set `HARNESS_ANALYST_MODEL` (`opus`/`sonnet`/`haiku`) to whatever your plan allows. |
