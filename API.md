# Lathe REST API (v0)

An **opt-in, local-first HTTP surface** for consumers that aren't MCP agents — a **web dashboard/UI**,
language-agnostic services, or CI-over-HTTP. Agents already have the full surface via **MCP** (`lathe_mcp.py`);
this adds the *non-agent* surface. It is an *additional* caller of the same gated engine — **no gate is
weakened, determinism/pins are unchanged.**

Server: `lathe_api.py` · start it with `lathe serve` · design rationale: `API_PROPOSAL_REST.md` (if present).

## Start it

```bash
export LATHE_API_TOKEN=$(openssl rand -hex 16)   # REQUIRED — no token => the server refuses to start
lathe serve                                       # binds 127.0.0.1:8799 (LATHE_API_PORT to change)
# non-local bind is gated: --bind 0.0.0.0 ALSO requires LATHE_SANDBOX=docker|docker-ssh
```

Every request needs `Authorization: Bearer $LATHE_API_TOKEN`. Base URL: `http://127.0.0.1:8799/v1`.

## Endpoints

### Read-only (synchronous, no model, no code run for the caller)
| Method & path | Wraps | Response |
|---|---|---|
| `GET /v1/env` | `lathe env` | the env **catalog** (name/group/role/default) — **never resolved values** |
| `GET /v1/plans` | `lathe plans` | `{plans: [...]}` |
| `GET /v1/metrics` | `lathe metrics summary` | `{metrics: "..."}` |
| `POST /v1/gate` | `lathe gate` | `{ok, report}` |
| `POST /v1/verify` | `lathe verify` | `{plan}` → `{ok, output}` (pin replay; 0 model calls) |
| `POST /v1/trace` | `lathe trace` | `{plan}` → `{ok, output}` (criterion→test→pin→model) |
| `POST /v1/review` | `lathe review` | `{files:[...], lenses?}` → `{ok, output}` |

### Builds (asynchronous jobs — may hit a model)
| Method & path | Behavior |
|---|---|
| `POST /v1/builds` | `{plan}` **or** `{goal}` (+ optional `env:{...}` allow-listed) → `202 {job_id, status}` |
| `GET /v1/builds/{job_id}` | `{status: queued\|running\|done\|failed, result?}` — `result` is the `lathe build --json` object; present only when terminal |

`status: done` with `result.build_ok: false` means **built, gate refused** — a successful *request*, a refused
*build*. Don't conflate the two.

```bash
# submit a plan build, poll the job
curl -s -XPOST localhost:8799/v1/builds -H "Authorization: Bearer $LATHE_API_TOKEN" \
     -H 'Content-Type: application/json' -d '{"plan":"projects/agentic-harness/plans/H_api_logic.py"}'
# => {"job_id":"job_1","status":"queued"}
curl -s localhost:8799/v1/builds/job_1 -H "Authorization: Bearer $LATHE_API_TOKEN"
# => {"status":"done","result":{"build_ok":true,"functions_passed":5,...}}
```

## Security model (what must be right)

- **Auth**: `LATHE_API_TOKEN` required; missing ⇒ server won't start; every call bearer-checked in **constant
  time** (`api_logic.auth_ok`).
- **Bind**: `127.0.0.1` by default; a non-local bind additionally requires a **docker sandbox tier** — the API
  never runs remote-submitted plan code in-process.
- **Input**: every `plan`/`files` path goes through `is_within_root` (no traversal); every free string through
  `reject_flags` (no `-flag` injection); a plan is still validated as data by the engine before import.
- **Caller `env` overrides**: **allow-list only** (`LATHE_STRICT`, `LATHE_ASSUMPTION_POLICY`, `LATHE_TEST_KIND`,
  `LATHE_MUTATION_SCORE`, `LATHE_REGRESSION_PROOF`, `LATHE_GATE_GLUE`, `LATHE_TEST_ACK`, `LATHE_TRIES`) — a
  caller can **never** set `LATHE_TRUST_PLAN`, `LATHE_SANDBOX`, endpoint URLs, or paths.
- **Secrets**: `GET /v1/env` returns the *catalog*, never resolved values.

## Scope (v0)

One trusted operator, one machine, opt-in. **Multi-tenant is out of scope** — per-tenant sandboxes, quotas, and
plan quarantine are a separate, larger design. The security-critical request logic (`api_logic.py`:
`bearer_token`/`auth_ok`/`env_allowlist`/`classify_build_body`/`job_view`) is **harness-built and gated**
(CRITERIA P1–P5); the HTTP glue is `lathe_api.py`, covered by `review_tests/test_api.py` (live server, real
token, real build job).
