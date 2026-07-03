# Lathe — CLI & Configuration Reference

*The complete, flat reference: every command, every user-facing flag, and every environment variable —
each with what it does, its default, and a runnable example. Source-grounded (extracted from `lathe.py`,
`engine_v2.py`, and `projects/agentic-harness/tools/`, verified against v2.6.2), so nothing here is
aspirational.*

- **New to Lathe?** Start with **`LATHE_GUIDE.md`** (install, prerequisites, your first build) — this file is
  the exhaustive option reference, not the tutorial.
- **Want prose + a worked example per command?** See **`LATHE_COMMANDS.md`**.
- This file is the "look up one option" manual.

---

## 1. Invocation & the two modes

```
lathe <command> [arguments] [flags]        # if the repo is on PATH
python lathe.py <command> [arguments] [flags]   # always works
```

Lathe runs in **two modes**, over the *same* command set:

| Mode | How | State |
|---|---|---|
| **One-shot** (default) | `lathe <command> …` runs once and exits | Stateless per call; only disk artifacts (pins, board, logs) persist. Use in scripts/CI. |
| **Interactive shell** | `lathe chat` opens a `lathe>` REPL | Session stays open; each line is a natural-language *goal* or a *command*. Survives transient endpoint/board failures (`lathe.py:195`). |

```
$ python lathe.py chat
lathe> slugify a title string     # a goal → analyst specs it, local model builds it, gate verifies, it pins
lathe> status                     # a command → runs in-session
lathe> build money.py             # every CLI command is available here too
lathe> quit
```

Every command below works in both modes.

---

## 2. Commands

Grouped by job. Argument conventions: `<required>`, `[optional]`, `a|b` = choose one. Only user-facing flags
are listed per command; the flat flag reference is §4.

### Build — turn a spec into gated, pinned code

| Command | What it does | Example |
|---|---|---|
| `lathe "<goal>"` / `lathe do "<goal>"` | One-shot: the analyst drafts a spec + tests, the local model implements, the gate verifies, the result is pinned. | `lathe do "parse '2h30m' into seconds"` |
| `lathe build <plan.py>` | Build an existing plan file (the reproducible unit of work). Rebuilds from pins are byte-identical, 0 model calls. | `lathe build plans/H_money.py` |
| `lathe chat` | Interactive REPL (see §1). | `lathe chat` |
| `lathe verify <plan.py>` | Prove the byte-identical claim: rebuild from pins offline and diff. | `lathe verify examples/hello.py` |
| `lathe sdlc "<goal>" [--out <dir>]` | The full pipeline in one command: clarify → assume → ack → STRICT build → trace → review. | `lathe sdlc "a rate limiter" --out ./out` |

### The two "no silent guessing" front-ends

| Command | What it does | Example |
|---|---|---|
| `lathe clarify "<goal>" [--answers <file>] [--out <dir>]` | Requirements liaison: interrogates a vague goal (inputs/outputs/success/edge/non-goals, pick-from options) and writes `CLARIFIED_GOAL.md` with testable acceptance criteria. | `lathe clarify "build a money parser"` |
| `lathe assume <plan.py> [--resolve\|--accept-all] [--answers <file>] [--scrutiny all\|high+med\|high\|off]` | Adversarial assumption auditor: surfaces the decisions the goal never made, materiality-ranked; under `LATHE_ASSUMPTION_GATE=1` the build refuses until each blocker is **resolved** (accept / pick / state intent) on a committed `<plan>.decisions.md`. | `lathe assume plans/H_money.py --resolve` |

### Quality — gates & review

| Command | What it does | Example |
|---|---|---|
| `lathe gate` | Run the standing regression gates (stale/dup/registry/pristine/lint/docs-drift). | `lathe gate` |
| `lathe lint-spec <plan.py>` | Test-quality probe: rejects tests a stub could pass. | `lathe lint-spec plans/H_money.py` |
| `lathe review [auto\|<lens…>\|all] <files…>` | Compound-Engineering persona review; `auto` lets the decider pick lenses (correctness/adversarial/security/…). | `lathe review auto engine_v2.py` |
| `lathe ack <plan> [--yes]` | Record human acknowledgement of a plan's exact test set (required when `LATHE_TEST_ACK=1`). | `lathe ack plans/H_money.py` |
| `lathe trace <plan> [model]` | Emit the traceability matrix: criterion → test → pin → model. | `lathe trace plans/H_money.py` |
| `lathe selftest` | Confirm the advertised capabilities are live via the CLI. | `lathe selftest` |

### Autonomy — the board & the driver

| Command | What it does | Example |
|---|---|---|
| `lathe auto "<objective>"` | Self-feed loop: decompose the objective and drive the board to green. | `lathe auto "add CSV export"` |
| `lathe decompose <plans…>` | Seed the board from plan files. | `lathe decompose plans/*.py` |
| `lathe run [N]` | Dispatch up to N board tasks. | `lathe run 4` |
| `lathe board` / `lathe status` | Show the task board / one-line status. | `lathe status` |
| `lathe wait <task>` / `lathe resume <task> [signal]` / `lathe waiting` | Park a task dormant / deliver a signal to resume / list dormant tasks. | `lathe waiting` |
| `lathe checkpoint [list \| snapshot [reason] \| restore <sha> --yes]` | Safe git rollback points (`refs/harness/ckpt`, never touches HEAD): list them, take a named snapshot, or restore one. A whole-tree `restore` **requires `--yes`** and takes a safety snapshot first. | `lathe checkpoint snapshot "before refactor"` |

### Introspection — know what's live

| Command | What it does | Example |
|---|---|---|
| `lathe whatis <capability>` | Which file is the canonical implementation of a capability. | `lathe whatis sandbox` |
| `lathe map <path…>` | Repo-map: symbol/signature outline (cheap context). | `lathe map projects/agentic-harness/tools` |
| `lathe dups` | Report duplicate basenames the pristine gate would flag. | `lathe dups` |
| `lathe plans` / `lathe metrics [summary]` | List plan files / show the metrics ledger. | `lathe metrics summary` |
| `lathe logs [<run_id>] [--tail] [--grep <s>]` | Structured run logs: list, tail the latest, or search. | `lathe logs --grep REFUSED` |

### Agents — expert personas on demand

| Command | What it does | Example |
|---|---|---|
| `lathe agent "<need>" [--spawn]` | Match an expert persona to a need; `--spawn` mirrors it locally (license-gated). | `lathe agent "adversarial reviewer" --spawn` |
| `lathe agent bucket` | Organize the persona library by when-to-invoke. | `lathe agent bucket` |
| `lathe agent rate [--all]` / `lathe agent ratings` | Field-probe + judge-score personas (`--all` grades every one, resumable) / show ratings. | `lathe agent rate --all` |
| `lathe agent refill` | Pre-mirror all permissive-license agents + licenses. | `lathe agent refill` |

### Maintenance

| Command | What it does | Example |
|---|---|---|
| `lathe clean [--dry]` | Quarantine stale/dup files (`--dry` previews, changes nothing). | `lathe clean --dry` |
| `lathe checkin [-m "msg"] [--push]` | Commit gated work (secret-scan first); `--push` also pushes upstream. | `lathe checkin -m "ship widget" --push` |
| `lathe report "<title>"` / `lathe issues` | File a self-diagnosing issue / list the issue queue. | `lathe report "gate flakes on empty plan"` |
| `lathe flow [<name>] [--run <targets>]` | Named contract-driven workflows (`code-review`, `bug-fix`, `enhancement`, `doc-review`, `new-project`, `sdlc`); dry-preview by default, `--run` executes. | `lathe flow doc-review --run README.md` |

---

## 3. Environment variables

Set them inline (`LATHE_X=… lathe …`), in your shell profile, or map them from `lathe.config.json` (§5).
**Precedence: an explicitly-set env var > config file > default.**

### 3a. Enforcement gates

`LATHE_STRICT=1` is the umbrella: when set to `1/true/yes/on` it arms the **seven gates** below *for keys you
haven't already set explicitly* (an explicit var always wins), and additionally requires declared `CRITERIA`
on `FUNCTIONS` plans and refuses `ARTIFACTS`-only plans (`strict_mode.py`, read at `engine_v2.py:98`).

| Variable | Controls | Values | Default | Set by STRICT? |
|---|---|---|---|---|
| `LATHE_STRICT` | The SDLC enforcement umbrella (arms the seven gates). | `1/true/yes/on` | off | — (it's the switch) |
| `LATHE_REGRESSION_PROOF` | A changed function must ship a test that **fails on the old** accepted code. | `1/true/yes/on` | off | ✅ `1` |
| `LATHE_TEST_ACK` | Refuses to build until the exact test set is human-acknowledged (`lathe ack`). | truthy | off | ✅ `1` |
| `LATHE_MUTATION_SCORE` | Min fraction of AST mutants the tests must kill, else REFUSE. | float `0.0`–`1.0` (garbage/out-of-range → gate skipped) | off | ✅ `0.5` |
| `LATHE_MUTATION_LIMIT` | Max mutants generated per function. | int > 0 | `8` | no |
| `LATHE_TEST_KIND` | Each function must ship the test **kinds** it declares (property/edge/roundtrip/error/example). | `1/true/yes/on` | off | ✅ `1` |
| `LATHE_GATE_GLUE` | Substantive hand-written `GLUE` must be exercised by an `INTEGRATION` test. | `1/true/yes/on` | off | ✅ `1` |
| `LATHE_GLUE_MAX` | Line count below which glue is "trivial" and not gated. | int | `2` | no |
| `LATHE_LINT_SPEC` | Spec-strength lint before the implementer runs. | `warn` (print) · `block` (refuse) · else off | off | ✅ `block` |
| `LATHE_ASSUMPTION_GATE` | Refuses to build while blocking-materiality assumptions are unresolved. | `1/true/yes/on` | off | ✅ `1` |
| `LATHE_ASSUMPTION_POLICY` | Which materiality blocks (the scrutiny dial). | `off/none/advisory` = none · `high` = high only · `med` = high+med · `all/low` = high+med+low | `high` | no (user-governed) |
| `LATHE_VALIDATE_PLAN` | Validate the plan as **data** before import (SSRF/RCE/OUT_DIR-escape guard). | `1` | off in the engine, **but the `lathe` CLI forces it on** (`lathe.py:1620`) | no (CLI-forced, not STRICT) |
| `LATHE_TRUST_PLAN` | Bypass the plan validator + OUT_DIR-escape check (trusted callers only). | `1` | off | no |

```bash
# Full rigor on one build:
LATHE_STRICT=1 lathe build plans/H_widget.py

# Tune the mutation gate without the whole umbrella:
LATHE_MUTATION_SCORE=0.7 LATHE_MUTATION_LIMIT=16 lathe build plans/H_widget.py

# STRICT, but make the assumption gate stricter than its default:
LATHE_STRICT=1 LATHE_ASSUMPTION_POLICY=high+med lathe build plans/H_widget.py
```

### 3b. Models & endpoints

| Variable | Controls | Default |
|---|---|---|
| `LATHE_MODEL` | Implementer model the CLI passes to the engine (`build`/`do`). | `openai:local` |
| `HARNESS_MODEL` | Engine-level implementer fallback when no model arg is given. | `gemma4:12b` (engine default) |
| `HARNESS_ANALYST_MODEL` | Model requested from the analyst (Claude) endpoint for spec generation. | `sonnet` |
| `HARNESS_CLAUDE_URL` | Analyst endpoint (OpenAI-compatible chat/completions). | `http://127.0.0.1:8787/v1/chat/completions` |
| `LATHE_TRIES` | Repair-loop attempt budget per plan. | `3` |
| `LATHE_MAX_RESP` | Cap on model response bytes (OOM guard). | `16777216` (16 MiB) |
| `LATHE_RATE_PACE` | Seconds between spawned agents (endpoint burst guard). | `2` |
| `LATHE_TRUST_REMOTE_ANALYST` | Allow a **non-local** analyst host (opens the SSRF guard). | off (non-local refused) |
| `LATHE_REVIEW_USE_CLI` | CE-review routing: `1` = Claude CLI first, `0` = endpoint-only, unset = auto. | auto |

```bash
# Point the analyst at your own key/endpoint and a bigger model:
HARNESS_CLAUDE_URL=https://api.internal/v1/chat/completions HARNESS_ANALYST_MODEL=opus \
  lathe do "add a CSV parser"

# Local implementer, more repair tries:
LATHE_MODEL=openai:local LATHE_TRIES=5 lathe build plans/H_widget.py
```

### 3c. Execution & sandbox

| Variable | Controls | Values | Default |
|---|---|---|---|
| `LATHE_SANDBOX` | Isolation level for running plan code + tests. | `subprocess` · `docker` · `docker-ssh` · `0/off/none/inproc` | unset → engine uses the in-process fast path; `subprocess` when the sandbox module is loaded |
| `LATHE_SANDBOX_TIMEOUT` | Hard timeout (s) for one sandboxed unit run. | int | `30` |
| `LATHE_RUN_TIMEOUT` | Operator ceiling (s) for an unattended CLI command (kills on exceed). | int; `0`/unset = unbounded | unbounded |
| `LATHE_DOCKER_IMAGE` | Image for the docker / docker-ssh sandbox (whitelist-validated). | `[A-Za-z0-9._/:-]+` | `python:3.12-slim` |
| `LATHE_DOCKER_SSH` | Remote SSH host for docker-ssh (also auto-selects docker-ssh with `LATHE_SANDBOX=docker`). | `[A-Za-z0-9._@-]+` | `rig` |
| `LATHE_AUTO_COMMIT` | Autonomy-loop git auto-commit opt-in. | `1/true/yes/on` = enable; other non-empty = disabled + warning | **off** (no commit) |

```bash
# Run untrusted plan code in a throwaway container:
LATHE_SANDBOX=docker LATHE_DOCKER_IMAGE=python:3.12-slim lathe build plans/untrusted.py

# On a remote rig over SSH:
LATHE_SANDBOX=docker-ssh LATHE_DOCKER_SSH=rig lathe build plans/untrusted.py

# Bound a long autonomous run to 30 minutes:
LATHE_RUN_TIMEOUT=1800 lathe auto "objective"
```

### 3d. Paths, config & observability

| Variable | Controls | Default |
|---|---|---|
| `LATHE_CONFIG` | Path to the single JSON config file. | `./lathe.config.json`, else `~/.lathe/config.json` |
| `LATHE_PROJECT` | Project-name label (issue records, etc.). | basename of the repo root |
| `LATHE_PRODUCT_GATES` | Dir of a consuming project's product gates. | `<root>/qa/gates` |
| `LATHE_LEDGER_DIR` | Docs/ledger dir. | `<root>/docs` |
| `LATHE_METRICS_PATH` | Where the metrics ledger (jsonl) is written. | `<root>/metrics/runs.jsonl` |
| `LATHE_LOG` | Enable structured per-run logging. | on (`0` disables) |
| `LATHE_LOG_DIR` | Run-log directory. | `<harness>/runs` |
| `LATHE_LOG_KEEP` | How many run logs to retain. | `100` |
| `LATHE_ISSUES_DIR` | Issue-queue directory. | `~/.lathe/issues` |
| `LATHE_REMOTE` | Git remote for `checkin` (overrides config `checkin.remote`). | — |

```bash
LATHE_CONFIG=./my.config.json lathe build plans/H_widget.py
LATHE_METRICS_PATH=/data/lathe/runs.jsonl lathe build plans/H_widget.py
LATHE_LOG_DIR=/var/log/lathe LATHE_LOG_KEEP=500 lathe do "add feature"
```

### 3e. Not environment variables (common confusion)

These names look like env vars but are **not** — don't try to set them:

- `LATHE_MARK`, `LATHE_ARTIFACT_MARK` — Python string constants stamped as line 1 of generated files
  (the "do not edit by hand" / "not a trusted prelude" markers), `engine_v2.py:191,195`.
- `LATHE_SB_RESULT` — the stdout framing marker `@@LATHE_SB_RESULT@@` for the sandbox's nonce-authenticated
  verdict, `sandbox.py:36`.
- `LATHE_ROOT` — appears only in comments/product scripts; the root is derived from the file path, never read
  from the environment.

### 3f. Internal / test-only (not for normal use)

`LATHE_VALIDATOR_PY`, `LATHE_SANDBOX_PY`, `LATHE_SANDBOX_PAYLOAD` (plumbing paths the CLI/parent set
automatically); `LATHE_GATE_RECORD`, `LATHE_CASSETTE`, `LATHE_CASSETTE_UPSTREAM`, `LATHE_CASSETTE_PORT`,
`LATHE_CASSETTE_STRICT`, `LATHE_CASSETTE_TIMEOUT` (record/replay HTTP cassette proxy for gate tests);
`LATHE_CE_PERSONAS` (override vendored persona dir); `LATHE_APP` (product-runner target URL). Documented for
completeness; leave unset in normal use.

> Note: `lathe_mcp.py` reads **no** environment variables of its own — the MCP surface inherits configuration
> from the engine/CLI it invokes.

---

## 4. CLI flags (flat reference)

| Flag | Command(s) | Effect | Without it |
|---|---|---|---|
| `--resolve` (alias `--confirm`) | `assume` | Walk each blocking assumption and decide it (accept / pick / state intent). | Prints blockers only; nothing resolved. |
| `--accept-all` | `assume` | Explicit bulk-accept of every blocker; logged as "accepted in bulk". Never the default. | Per-item decisions. |
| `--answers <file>` | `assume`, `clarify` | Read one decision/answer per item from a file (scripted/CI). | Interactive prompts on stdin. |
| `--scrutiny <lvl>` | `assume` | Set what materiality blocks: `all` / `high+med` / `high` / `off`. | Falls back to `LATHE_ASSUMPTION_POLICY` → `high`. |
| `--policy <lvl>` | `assume` | Alias of `--scrutiny`. | Same as above. |
| `--out <dir>` | `clarify`, `sdlc` | Output directory for the generated brief / artifacts. | clarify → default dir; sdlc → required. |
| `--run [targets…]` | `flow` | Execute the workflow's `[AUTO]`/`[GATE]` steps. | Dry preview of the steps only. |
| `--dry` | `clean` | Preview quarantine actions; change nothing. | Performs the cleanup. |
| `--spawn` | `agent` | Mirror the matched agent locally (with its license). | Prints fetch info only. |
| `--push` | `checkin` | Also push upstream after commit (secret-scan first). | Commits locally only. |
| `--tail` | `logs` | Show the most recent run's full trace. | Lists recent runs. |
| `--grep <s>` | `logs` | Substring-search across all run logs. | List/trace mode. |
| `--all` | `agent rate` | Grade every agent (resumable; skips already-rated). | Rates a single target. |
| `--yes` | `ack`, `checkpoint restore` | Skip the confirmation prompt / allow a destructive whole-tree restore. | `ack` prompts; `restore` refuses without it. |

```bash
lathe assume plans/H_widget.py --resolve --scrutiny high+med
lathe assume plans/H_widget.py --resolve --answers answers.txt      # one decision per line, CI-safe
lathe clarify "build a CSV linter" --out ./briefs --answers ans.txt
lathe flow bug-fix --run plans/H_widget.py
lathe clean --dry
lathe agent "adversarial reviewer" --spawn
lathe checkin -m "ship widget" --push
lathe logs --tail
lathe logs --grep REFUSED
lathe agent rate --all
lathe ack plans/H_widget.py --yes
```

---

## 5. Config file — `lathe.config.json`

A single optional JSON file (found via `LATHE_CONFIG`, else `./lathe.config.json`, else
`~/.lathe/config.json`). Keys map to the env vars above; **env vars still win over the file.** Common keys:

```json
{
  "analyst":  { "url": "http://127.0.0.1:8787/v1/chat/completions", "model": "sonnet" },
  "implementer": { "model": "openai:local" },
  "tries": 3,
  "assumptions": { "scrutiny": "high" },
  "checkin": { "remote": "origin" }
}
```

| Config key | Maps to | 
|---|---|
| `analyst.url` | `HARNESS_CLAUDE_URL` |
| `analyst.model` | `HARNESS_ANALYST_MODEL` |
| `implementer.model` | `HARNESS_MODEL` |
| `tries` | `LATHE_TRIES` |
| `assumptions.scrutiny` | `LATHE_ASSUMPTION_POLICY` |
| `checkin.remote` | `LATHE_REMOTE` |

---

## 6. Quick recipes

```bash
# The honest 5-minute test
lathe verify examples/hello.py                     # pins replay, byte-identical, 0 tokens
lathe do "a function that parses '2h30m' into seconds"

# Full-rigor build with the audit trail
LATHE_STRICT=1 lathe clarify "a money parser"      # step 0: interrogate the goal
LATHE_STRICT=1 lathe assume plans/H_money.py --resolve   # step 0.5: resolve silent assumptions
LATHE_STRICT=1 lathe build plans/H_money.py        # seven gates enforce it
lathe trace plans/H_money.py                        # emit criterion → test → pin → model

# Untrusted plan, contained
LATHE_SANDBOX=docker lathe build plans/from_the_internet.py

# CI-safe, non-interactive
LATHE_STRICT=1 lathe assume plans/H_money.py --resolve --answers ci_answers.txt
```

---

*Grounded in source at v2.6.2. If a flag or variable here ever drifts from behavior, the code is the oracle —
file a `lathe report` and it'll be corrected.*
