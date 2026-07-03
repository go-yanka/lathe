# Guide — Lathe as an MCP tool (drive it from Claude Code / Cursor / Copilot)

*Lathe ships a minimal, stdlib-only **MCP server** (`lathe_mcp.py`) that exposes its deterministic
build / gate / pin / review as **tools** over stdio JSON-RPC 2.0. Point any MCP client at it and the agent
you already use gains Lathe's hard test-gate, content-hash pinning, and provenance — Lathe becomes the
**build layer under your agent**.*

This is the programmatic "API" today: not REST, but the tool interface every modern coding agent speaks.

Related: `QUICKSTART_STANDALONE.md` · `CLI_REFERENCE.md` · `GUIDE_MODELS_AND_AGENTS.md`.

---

## Register it (one config block)

Add Lathe to your MCP client's server list:

```json
{
  "mcpServers": {
    "lathe": { "command": "python", "args": ["lathe_mcp.py"] }
  }
}
```

- **Claude Code / Claude Desktop** → the `mcpServers` block in its MCP config.
- **Cursor / Copilot / any MCP client** → the same shape, wherever it keeps MCP servers.
- Use an absolute path to `lathe_mcp.py` (or run the client from the repo root) so `python lathe_mcp.py`
  resolves.

The server is **stdlib-only** — no install step beyond having the repo and Python ≥3.10.

---

## The tools it exposes

| Tool | Arguments | What it does |
|---|---|---|
| `lathe_do` | `goal` (string) | From a natural-language goal: draft a spec + tests, build on the local model under the gate, pin. |
| `lathe_build` | `plan` (path) | Build a plan: generate each function under the hard test gate; pin passing code so rebuilds are byte-identical. |
| `lathe_verify` | `plan` (path) | Rebuild from pins and confirm reproducibility (zero model calls when pinned). |
| `lathe_gate` | *(none)* | Run the standing tree gates (stale/dups/registry/pristine/lint/docs-drift/env-drift) + regression. |
| `lathe_review` | `files` (paths), `lenses` (optional, e.g. `"correctness adversarial security"`) | Multi-lens CE review of files. |

**Model-independent by design:** the *client's* model calls these tools; Lathe runs the gate/pin locally
against whatever analyst/implementer endpoints **you** configured (see `GUIDE_CLAUDE_SUBSCRIPTION.md` /
`GUIDE_MODELS_AND_AGENTS.md`). The agent decides *what* to build; Lathe decides *what's allowed to ship*.

---

## Typical flow inside an agent

1. You ask your agent (in Claude Code, say) to add a function.
2. The agent calls **`lathe_do`** with the goal → Lathe specs it, builds it on your local model under the
   gate, and pins it. The agent gets back the result, not a pile of unverified code.
3. The agent calls **`lathe_verify`** to prove the build is reproducible, or **`lathe_gate`** before it
   commits.
4. You get gated, pinned, provenance-carrying code from the agent you were already using — the agent can't
   hand you code that didn't pass.

---

## Security — what the server refuses

The MCP surface is **input-guarded** (harness-built `mcp_safe.py`), because tool arguments come from a model:

- **No argument injection** — any argument beginning with `-` is refused (a client can't smuggle CLI flags).
- **No path traversal** — `plan`/`files` must resolve *inside the project root* (`is_within_root`, symlink-safe);
  `..` and absolute escapes are refused.
- **`goal` is guarded too** — must be non-empty and not start with `-`.

The server reads **no environment variables of its own** — it inherits the analyst/implementer configuration
from the CLI/engine it shells into. **Important:** the env it inherits is the **MCP client's launch
environment** (e.g. the Claude Code / Cursor process), *not* your interactive shell — so exporting
`HARNESS_CLAUDE_URL`/`LATHE_MODEL` in your terminal won't reach an MCP-driven build. Under MCP, configure the
analyst/implementer in **`lathe.config.json`** (which the engine loads regardless of who launched it), or
export the vars into the client's own launch environment. Otherwise `lathe_do`/`lathe_build` can run with no
analyst endpoint set even though the same config "works" from your shell.

---

## Honest status

MCP is **built and tested**, and it's the real programmatic interface for **agents**. If you need to drive
Lathe from something that isn't an MCP client (a web dashboard, a language-agnostic service, CI over HTTP),
there's now an opt-in **HTTP/REST API** too (`lathe serve`, v2.8.0 — see `API.md` / `docs/API_PROPOSAL_REST.md`).
For any agent that speaks MCP, this MCP surface is the shipped path; for non-agent HTTP consumers, use the
REST API.
