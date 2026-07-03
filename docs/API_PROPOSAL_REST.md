# Proposal — an HTTP/REST API for Lathe

*Status: **IMPLEMENTED in v2.8.0** (`main` @ `25b1759`) — the maintainer built the full v0 from this design.
The shipped surface is documented in **`API.md`**; start it with `lathe serve` (or
`LATHE_API_TOKEN=… python lathe_api.py`). This document remains the **design of record** and the rationale.
An adversarial security review of the implementation was run against v2.8.0 (auth, path-escape,
env-override leakage) and its findings are on PR #1 — the auth/traversal/env-isolation core held; two items
(the API token in child-process env, and gate-refused builds reporting `status:"failed"`) were flagged for
hardening.*

Related: `GUIDE_MCP.md` (the programmatic surface that exists today) · `CLI_REFERENCE.md` (the commands an API
would wrap) · `SECURITY.md`.

---

## 1. Why (and why not)

Lathe already has three programmatic surfaces: the **CLI**, **Python-embed** (`import` the engine), and
**MCP** (`lathe_mcp.py`, the agent tool interface). MCP covers the agent-integration case well — Claude Code,
Cursor, Copilot drive Lathe today.

A **REST/HTTP API** is the missing surface for consumers that are *not* MCP agents:

- a **web dashboard / UI** (submit a goal, watch the build, browse the pin ledger);
- **language-agnostic callers** (a Go/Rust/JS service that shouldn't shell out or speak MCP);
- **CI/CD over HTTP** (a pipeline step that POSTs a plan and gates the response) — cleaner than shelling `lathe`;
- a future **hosted / multi-tenant** offering.

**Why *not*, stated against interest.** Lathe's whole safety story is *local-first*: model-written code runs
in a sandbox on the same machine that owns the plan. An HTTP API invites running that code **on behalf of a
remote caller**, which reintroduces exactly the risks the design avoids — untrusted plans, multi-tenant
isolation, auth, resource abuse. So the API must be **opt-in, authenticated, local-bound by default**, and it
must not weaken any gate. If you don't have a non-agent consumer, **MCP is enough — don't build this yet.**

---

## 2. Design principles

1. **Wrap the engine, don't fork it.** Every endpoint calls the same code path as the CLI (ideally reusing the
   `--json` result object), so there is **one build path** and the gates can't diverge between CLI and API.
2. **Refuse by default, exactly like MCP.** Reuse `mcp_safe` (`reject_flags`, `is_within_root`): no flag
   injection, no path traversal, plan/goal validated as data.
3. **Local-bind + auth required.** Default bind `127.0.0.1`; a token is required for every call; binding to
   `0.0.0.0` requires an explicit flag *and* forces the container sandbox tier.
4. **Async where builds are slow.** A build can take minutes on a cold model, so builds are **jobs** (submit →
   poll / stream), not blocking requests.
5. **The response is the `--json` object.** v2.7.0 already emits a stable build JSON (`build_ok`,
   `functions_passed/total`, `per_function`, tokens, timings). The API returns exactly that — no new schema to
   keep in sync.

---

## 3. Proposed surface (v0)

Base: `http://127.0.0.1:8799/v1`. Every request carries `Authorization: Bearer <LATHE_API_TOKEN>`.

### Synchronous (fast, model-independent)

| Method & path | Wraps | Body → Response |
|---|---|---|
| `POST /v1/verify` | `lathe verify` | `{plan}` → the build JSON (pin replay; 0 model calls) |
| `POST /v1/gate` | `lathe gate` | `{}` → `{gates:[{name,ok,detail}], ok}` |
| `POST /v1/review` | `lathe review` | `{files:[…], lenses?:"…"}` → `{findings:[…]}` |
| `POST /v1/trace` | `lathe trace` | `{plan}` → the traceability matrix (criterion→test→pin→model) |
| `GET  /v1/env` | `lathe env` | → the `env_catalog.py` registry (names/roles/defaults; **never values**) |
| `GET  /v1/plans` · `GET /v1/metrics` | `lathe plans` / `metrics` | → listings |

### Asynchronous (builds — may hit a model)

| Method & path | Wraps | Behavior |
|---|---|---|
| `POST /v1/builds` | `lathe build <plan>` / `lathe do <goal>` | `{plan}` **or** `{goal}` (+ optional `strict:true`, `env:{…}` allow-listed) → `202 {job_id}` |
| `GET  /v1/builds/{job_id}` | — | → `{status: queued\|running\|done\|failed, result?: <build JSON>}` |
| `GET  /v1/builds/{job_id}/events` | — | SSE stream of gate/attempt events (optional) |

`result` is the v2.7.0 `--json` object verbatim. `status:done` + `result.build_ok:false` means "built, gate
refused" — a successful *request*, a refused *build* (don't conflate them in status codes).

---

## 4. Security model (the part that must be right)

- **Auth:** `LATHE_API_TOKEN` (env). No token set → server refuses to start. Constant-time compare.
- **Bind:** `127.0.0.1` only unless `--bind 0.0.0.0` is passed **and** `LATHE_SANDBOX=docker`/`docker-ssh` is
  set — never run remote-submitted plan code in-process.
- **Input:** every `plan`/`files` path goes through `is_within_root`; every string field through
  `reject_flags`; a submitted **plan body** (if you allow inline plans, not just server-side paths) goes
  through the existing `LATHE_VALIDATE_PLAN` data-validator before anything is imported.
- **`env` overrides in a request:** allow-list only (e.g. `strict`, `scrutiny`, `tries`) — never let a caller
  set `LATHE_TRUST_PLAN`, `LATHE_SANDBOX`, endpoint URLs, or paths.
- **Resource limits:** per-token concurrent-job cap; `LATHE_RUN_TIMEOUT` enforced per job; response size cap.
- **Secrets:** `GET /v1/env` returns the *catalog* (names/roles/defaults), never resolved values.
- **Multi-tenant:** out of scope for v0. v0 is "one trusted operator, one machine, opt-in." Multi-tenant is a
  separate, larger design (per-tenant sandboxes, quotas, plan quarantine).

---

## 5. What it does NOT change

- No gate is weakened or bypassed; the API is a caller of the same engine, subject to the same
  `LATHE_STRICT` composition.
- Determinism/pins are unchanged — a build via the API pins exactly as the CLI would.
- MCP and the CLI stay; this is an *additional* surface, not a replacement.

---

## 6. Suggested build order (small, gated, dogfooded)

1. **Sync read-only first** (`/gate`, `/verify`, `/env`, `/plans`, `/metrics`) — no model, no code execution
   on behalf of a caller, low risk. Ships value immediately (a dashboard can read state).
2. **Auth + local-bind + input guards** — before any write/build endpoint exists.
3. **Async builds** (`/builds`) last, with the container-sandbox requirement wired in.
4. Build the server itself **through Lathe** where possible (the pure request/response-shaping helpers are
   gate-able functions); the HTTP glue is GLUE (gate it with an integration test under `LATHE_GATE_GLUE`).

---

## 7. Does this make Lathe more versatile? — the honest answer

**Yes, for non-agent consumers** (web UI, language-agnostic services, CI-over-HTTP, hosted). **No net-new
versatility for agents** — MCP already gives them the full surface. So the value depends entirely on whether
those non-agent consumers are on the roadmap. If a web UI or a hosted offering is a goal, this is the
enabling layer and the **read-only sync slice is worth building now**. If the near-term audience is
developers-at-a-terminal and agents, the CLI + MCP already cover it, and this can wait.

Recommendation: **build the read-only sync slice** (steps 1–2) — it's low-risk, immediately useful for a
dashboard, and defers the genuinely hard part (running remote-submitted plan code safely) until there's a
concrete consumer that needs it.
