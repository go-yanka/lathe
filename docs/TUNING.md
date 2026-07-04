# Lathe — Tuning Guide

*The knobs, organized by **what you're trying to achieve** and **what each one trades**. Every variable here
is real (it's in `env_catalog.py`, printed by `lathe env`, and enforced-complete by the env-drift gate); this
guide adds the *why* the flat references don't. For per-flag detail see `CLI_REFERENCE.md`; for the gates
specifically see `GATES_REFERENCE.md`.*

> **Precedence everywhere:** explicit env var **>** `lathe.config.json` **>** built-in default.

---

## 1. Turn up correctness / rigor

You want the build to refuse more, guess less. See `GATES_REFERENCE.md` for the full mechanics; the knobs:

| Var | Turn it… | Trade |
|---|---|---|
| `LATHE_STRICT=1` | on | arms all seven rigor gates + requires `CRITERIA`. The production posture. |
| `LATHE_MUTATION_SCORE` | up (e.g. `0.8`) | tests must kill more mutants → stronger suites, but more build refusals to work through |
| `LATHE_MUTATION_LIMIT` | up | more mutants probed per function → tighter signal, slower gate |
| `LATHE_GLUE_MAX` | down | less hand-written glue allowed without an INTEGRATION test |
| `LATHE_ASSUMPTION_POLICY` | `all` | every material assumption (high+med+low) blocks until resolved → maximum "no silent guessing," more upfront questions |
| `LATHE_TEST_KIND` + plan `kinds` | on | force property/edge/error tests per contract |

Remember explicit vars win: `LATHE_STRICT=1 LATHE_MUTATION_SCORE=0.9` is STRICT-but-stricter. To drop one
gate under STRICT use a **non-empty** disabling value (`LATHE_TEST_ACK=0`), not an empty string.

## 2. Cut cost & latency

Local builds are free per token but not free of wall-clock. Where the time goes and how to trim it:

| Var | Effect | Trade |
|---|---|---|
| `LATHE_TRIES` (default 3) | down → fewer implementer attempts before escalating | faster, but more escalations to you on hard functions |
| plan `"select": N` | per-function best-of-N | `1` (default) is fastest; `2`/`3` spend more calls to pick the cleanest — reserve for complex units |
| `LATHE_MUTATION_LIMIT` | down | cheaper mutation gate |
| `LOCAL_OPENAI_MAXTOK` | down | caps runaway generations; too low truncates valid code |
| `LOCAL_GEN_TIMEOUT` / `CLAUDE_TIMEOUT` | match your models | a slow local model needs a higher gen timeout; a fast one can fail faster |
| pins | — | the biggest lever: an unchanged spec rebuilds from `.pins.json` with **zero** model calls (see `PINS_REFERENCE.md`). Keep `.pins.json` checked in. |

The single most effective cost move isn't a flag — it's **not regenerating**: stable specs ride the pin cache.

## 3. Isolation & security

Plan code is *executed* to run its tests. Match the isolation tier to how much you trust the plan.

| Var | Value | When |
|---|---|---|
| `LATHE_SANDBOX` | `subprocess` | your own validated plans (default for autonomy) |
| | `docker` | untrusted plans — run tests in a container |
| | `docker-ssh` | untrusted plans on a remote host (required for a non-local REST bind) |
| `LATHE_SANDBOX_TIMEOUT` | seconds | bound runaway test code (see the open sandbox timeout issue — set this) |
| `LATHE_DOCKER_IMAGE` / `LATHE_DOCKER_SSH` | image / host | wire up the docker tiers |
| `LATHE_MAX_RESP` | bytes | cap what an endpoint can return (defensive against a hostile/broken endpoint) |
| `LATHE_API_TOKEN` | required | the REST API refuses to start without it; bearer auth (constant-time) |
| `LATHE_API_PORT` | default 8799 | REST bind port |

**Danger flags — leave off unless you mean it:**

- `LATHE_TRUST_PLAN=1` — allows a plan's `OUT_DIR` to escape the project tree. Off by default for good reason.
- `LATHE_TRUST_REMOTE_ANALYST=1` — opens the SSRF guard on a non-local analyst endpoint. Only for an analyst
  URL you fully control.

## 4. Deterministic testing (record / replay)

To test the harness itself without hitting a live model, use the **cassette** proxy — record real
model responses once, replay them deterministically:

| Var | Role |
|---|---|
| `LATHE_CASSETTE` | cassette file to record into / replay from |
| `LATHE_CASSETTE_UPSTREAM` | the real endpoint to record from |
| `LATHE_CASSETTE_PORT` | proxy port (default 8791) |
| `LATHE_CASSETTE_STRICT=1` | fail on a cassette miss instead of silently passing through to the live endpoint |
| `LATHE_CASSETTE_TIMEOUT` | upstream timeout while recording |

`LATHE_CASSETTE_STRICT=1` is the one to set in CI — otherwise a missing cassette entry silently becomes a
live call, which is both non-deterministic and possibly costly.

## 5. Autonomy

For `lathe auto` / `do` / `run` (the objective→spec→build→gate→commit loop):

| Var | Note |
|---|---|
| `LATHE_AUTO_COMMIT` | **opt-in.** Off by default — autonomy will build and gate but not touch git until you set this |
| `LATHE_PROJECT` | which subtree under `projects/` is active (default `agentic-harness`) |
| `LATHE_REMOTE` | git remote for `checkin --push` (default `origin`) |

`LATHE_AUTO_COMMIT` off is the safe default: you get the green builds without surprise commits. Turn it on
only once you trust the loop on your project.

## 6. Observability & storage

| Var | Role | Default |
|---|---|---|
| `LATHE_METRICS_PATH` | the run ledger (`runs.jsonl`) — your provenance + benchmark data | `metrics/runs.jsonl` |
| `LATHE_LOG_DIR` / `LATHE_LOG` / `LATHE_LOG_KEEP` | structured per-run logs, and how many to retain | `runs/` |
| `LATHE_LEDGER_DIR` / `LATHE_ISSUES_DIR` | failure ledger / issues locations | — |
| `LATHE_CONFIG` | path to `lathe.config.json` (else `./` or `~/.lathe/`) | — |

The ledger is not just logs — it's the artifact the provenance and model-benchmark stories rest on
(`MARKETING_SALES_KIT.md §6`). Point `LATHE_METRICS_PATH` somewhere durable if you care about that history.

## 7. Endpoints (where the two brains live)

| Var | Role |
|---|---|
| `HARNESS_CLAUDE_URL` / `HARNESS_ANALYST_MODEL` | the **analyst** (thinker) endpoint + model |
| `LATHE_MODEL` / `HARNESS_MODEL` | the default **implementer** (builder) model |
| `LOCAL_OPENAI_URL` / `OLLAMA_URL` | where `openai:*` / bare-name implementer models resolve |

Point `HARNESS_CLAUDE_URL` at `claude_proxy.py` to drive the analyst from a Claude subscription at $0/token
while a local implementer does the volume — see `GUIDE_CLAUDE_SUBSCRIPTION.md`.

---

## The short version

- **Want it stricter?** `LATHE_STRICT=1`, then raise `LATHE_MUTATION_SCORE` / `LATHE_ASSUMPTION_POLICY=all`.
- **Want it faster/cheaper?** Lower `LATHE_TRIES`, keep `"select": 1`, and lean on the pin cache.
- **Running untrusted plans?** `LATHE_SANDBOX=docker` + `LATHE_SANDBOX_TIMEOUT`, and never set the trust flags.
- **Testing in CI?** Cassettes with `LATHE_CASSETTE_STRICT=1`.
- **Automating?** `LATHE_AUTO_COMMIT` stays off until you trust the loop.

*`lathe env` prints the live catalog (names/roles/defaults, never resolved secret values). This guide is the
map of *when* to reach for each; that command is the always-current index.*
