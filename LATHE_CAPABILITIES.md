# Lathe — Capabilities Catalog

> **Treat AI code generation like a build system, not a conversation.**
> The authoritative, file‑cited map of everything Lathe can do. This is the spine the CLI and the
> a prior agent `/` slash‑commands reference — if a capability isn't here, it isn't discoverable, and an
> autonomous agent will never reach for it. Status legend: **✅ wired** (the autonomous self‑feed loop
> uses it today) · **🔌 available** (built + tested, not yet on the autonomous path) · **🧠 analyst** (a
> human/premium‑model front‑end step, not the autonomous loop).

Two trees share **one byte‑identical engine**: the canonical meta‑tool
(`<LATHE_ROOT>\projects\agentic-harness`, plus the product `projects\your-product` where the
H3–H6 gates live) and the live autonomous copy (`<LATHE_ROOT>`). Paths below are relative to
a tree unless absolute.

---

## 0. Current capabilities (2026-07 — the real, shipped state)

The catalog below (§1+) is the original design map; these are the capabilities added since, now live in
canonical `2026-07-01q`. Project-facing how-to-use: **`FOR_PROJECTS.md`**; every command with an example:
**`LATHE_COMMANDS.md`**.

| Capability | What it is | Entry point |
|---|---|---|
| **Test-quality linter** | mutation probe — flags tests a trivial impl could pass | `lathe lint-spec`, `tools/spec_lint.py` |
| **Docker-SSH sandbox** | untrusted code in a network-less read-only container on a remote host | `LATHE_SANDBOX=docker-ssh`, `tools/sandbox.py` |
| **Structured logging** | per-run `runs/<id>.jsonl`, secrets redacted | `lathe logs`, `tools/run_logger.py` |
| **Metrics surface** | build success / cost / churn from the ledger | `lathe metrics summary`, `tools/metrics_summary.py` |
| **Data-quality primitives** | distribution-anomaly / dangling-refs / incomplete-records | `DATA_QUALITY.md` + those `tools/*.py` |
| **Cassette (record/replay)** | deterministic offline LLM-pipeline e2e gates | `tools/cassette_proxy.py` |
| **Real CE review** | vendored Compound-Engineering personas (v3.17.0) + Lathe doctrine | `lathe review`, `ce_personas/`, `hreview.py` |
| **Repo-map** | multi-language code structure via universal-ctags | `lathe map`, `tools/repomap.py` |
| **Workflows** | named ordered processes (review/bug-fix/enhancement/…) | `lathe flow`, `tools/workflows.py` |
| **Non-functional + docs gates** | ruff real-bug lint + docs-drift, in `run_gates` | `qa/lint_gate.py`, `qa/docs_drift_gate.py` |

Also since the original catalog: engine hardening (atomic writes, pin rollback, prelude fail-loud), a
MODULE_NAME path-traversal guard, cross-platform fixes, and a full self-review pass (Lathe reviewing its own code).

---

## 1. The core idea

A **plan** (`plans/NN_name.py`) is the regenerable source of truth for a module: per‑function design +
expectations + tests. A premium model (the **analyst** — human or Claude) writes the plan; a cheap
**local** model generates the code; **gates** judge it; accepted output is **pinned** by
`hash(spec+tests+model)` so rebuilds are byte‑identical; every failure is **banked** to sharpen the
spec. Three deliberate, unusual choices: **no model escalation on failure**, **content‑hash pinning**,
**live‑browser behavioral gating**.

```
Analyst (you + premium model) ──writes──▶ spec + tests   ◀── source of truth
        │ build
        ▼
Local model ──generates──▶ code            ◀── the cheap "compiler"
        │
        ▼  Gate: unit tests · live-browser behavioral test · design contract
   FAIL │                          │ PASS
        ▼                          ▼
   Bank failure + sharpen spec   Pin it: hash(spec+tests+model) → reproducible rebuild → ship
        └───────(no escalation to a bigger model)──────▶ back to the spec
```

---

## 2. The plan format (the contract the engine reads)

`engine_v2.py` reads these fields. **Module‑level:** `MODULE_NAME, OUT_DIR, HEADER, FUNCTIONS, GLUE,
INTEGRATION, ARTIFACTS, PRELUDE, RETIRE`. **Per‑function** (`FUNCTIONS[]`): `name, prompt, tests,
context, model, level, select`. **Per‑artifact** (`ARTIFACTS[]`): `path, prompt, model, tests,
functional, fallback, fallback_after, skeleton, fill_marker`.

- `HEADER` — code prepended verbatim (imports + analyst‑authored hard logic the model shouldn't write).
- `GLUE` — hand‑authored wiring appended verbatim (never generated).
- `INTEGRATION` — an assert script that the assembled module must pass as a whole.
- `PRELUDE` — earlier built modules to exec into namespace so this plan can call them.
- Numeric filename prefix (`01_`, `02_`) **is** the dependency order.

---

## 3. Engine build modes & features (`engine_v2.py`)

| Capability | What it does | Invoke via | Status |
|---|---|---|---|
| **Plan‑driven build** | Loads a plan, builds each unit best‑of‑N under test‑gating; no LLM in the driver | `python engine_v2.py <plan> [model] [N]` | ✅ |
| **Implementer routing** | Routes generation to `openai:local` (rig/local), ollama, or `claude` | per‑call `model` arg | ✅ (local) |
| **Per‑function model / levels** | Plan picks model or level per function; engine **sticks** (failure → sharpen spec, never silent swap) | `FUNCTIONS[].model` / `.level` | 🔌 (claude/level‑2 unused) |
| **Best‑of‑N** | Up to N candidates, temperature ramp | CLI `N` (autonomy uses 3) | ✅ |
| **Select‑K quality judge (D28)** | Collect K *passing* candidates, Claude picks the cleanest (deterministic score fallback) | `FUNCTIONS[].select = 2/3` | 🔌 |
| **Skeleton‑fill (token reduction)** | Model returns only a small `__FILL__` region spliced into a scaffold → far fewer tokens | artifact `skeleton` + `fill_marker` | 🔌 |
| **Skeleton‑complete (0‑token)** | Scaffold has no `__FILL__` → skip the model entirely, gate deterministically (3× flake‑retry) | `skeleton` without the marker | 🔌 |
| **Artifact / whole‑file output** | Model writes a whole file (UI/API/config) from prompt+tests; fence/preamble salvage | `ARTIFACTS[]` | 🔌 |
| **Structural gate** | Runs artifact asserts against the generated `content` | `ARTIFACTS[].tests` | 🔌 |
| **Functional gate (behavioral)** | Writes content to a temp file, runs a `functional` script (e.g. Playwright); exit 0 = pass | `ARTIFACTS[].functional`; env `FUNC_GATE_TIMEOUT` | 🔌 |
| **Artifact fallback/escalation** | After `fallback_after` fails on primary, escalate to `fallback` model (artifact lane only) | `ARTIFACTS[].fallback/_after` | 🔌 |
| **STRICT validation gate** | Execs `HEADER+code` in a clean namespace, runs each assert | `FUNCTIONS[].tests` | ✅ |
| **Content‑hash pinning (D27)** | Approved impl keyed by `sha256(name+prompt+tests+model)`, reused while it still passes → byte‑stable rebuilds | auto; `<OUT_DIR>/.pins.json` | ✅ |
| **Failure‑as‑asset (functions)** | Failed candidate + **exact failing test/error** → `_fn_fails/<name>.<model>.attemptK.py` + `.reason.txt` | auto on fail | ✅ (read back by repair loop) |
| **Failure‑as‑asset (artifacts)** | Failed artifact + reasons → `_artifact_fails/` | auto | 🔌 |
| **timeout ≠ fail** | A gate timeout is reported as slow/flaky, **not** banked as a spec failure | env `*_TIMEOUT` | ✅ |
| **Module assembly (GLUE)** | On all‑green, assembles `HEADER+funcs+GLUE` → `<MODULE_NAME>.py` | plan fields | ✅ |
| **Integration test** | Runs `INTEGRATION` as `itest.py` in OUT_DIR; PASS/FAIL/TIMEOUT | `INTEGRATION` | 🔌 |
| **Analyst‑directed retirement** | Archives `RETIRE` files to `_archive/<date>-<plan>/` + REASON.md | `RETIRE` | 🔌 |
| **Standing regression gate** | Runs `qa/run_gates.py`; was‑green‑now‑red fails the build | env `SKIP_REGRESSION`, `RUN_GATES_PATH` | ✅ |
| **Run report + metrics** | `RUN_REPORT.md` + `===METRICS_JSON===` + `runs.jsonl` + token accounting | auto | ✅ |

**`claude_proxy.py`** — OpenAI‑compatible shim over the `claude -p` CLI (the analyst brain, $0 via
subscription / BYO key). `POST /v1/chat/completions`, `/v1/models`, `/health`; tools disabled. ✅ used
for every planner/repair/judge call.

---

## 4. Quality gates

Real **H3–H6 gates live in `projects/your-product/qa/gates/`** (the agentic‑harness tree has only the
regression aggregator).

| Gate | What it does | Invoke | Status |
|---|---|---|---|
| **H3 visual‑regression** | Playwright screenshot at fixed viewport (APIs stubbed) + PIL pixel‑diff vs approved baseline | `python qa/gates/visual_gate.py [--update-baseline]` | 🔌 |
| **H4 performance** | HTML/inline‑script weight + Nav‑Timing DCL/load + live API latency budgets | `python qa/gates/perf_gate.py [--no-api]` | 🔌 |
| **H5 security** | bandit SAST (gates on HIGH) + SSRF probe (internal/metadata URLs must 400) + deps‑pinning report | `python qa/gates/security_gate.py [--no-live]` | 🔌 |
| **H6 accessibility** | Serves UI + axe‑core; gates on NEW serious/critical beyond baseline (brownfield ratchet) | `python qa/gates/a11y_gate.py [--strict]` | 🔌 |
| **run_all** | Runs H3–H6, aggregates | `python qa/gates/run_all.py` | 🔌 |
| **run_gates / stale_gate** | Post‑build regression + fails build if backup/dup/stale files linger | wired into engine; `python qa/stale_gate.py` | ✅ |
| **road_ready (whole‑product)** | Fresh‑subprocess import → boot+HTTP‑health → live‑E2E/smoke; fail‑closed | via `driver.py` when a plan declares `ROAD_READY` | 🔌 |

Product gates (your-product): `drift_gate`, `functional_acceptance`, `gate_db_schema/project`,
`tenant_isolation`, `source_completeness_gate`, page gates, `_e2e_harness.py` skeleton‑fill E2E. 🔌

---

## 5. Token reduction

The token win is **skeleton‑fill**: move hard/boilerplate logic into the hand‑authored scaffold so the
local model fills only a tiny, well‑bounded region (or none — skeleton‑complete = 0 tokens). This is the
"code structure that reduces the higher/local model's tokens." (`token_overlap.py` is a separate text
helper, not a token‑budget reducer.) `decompose.py` (A6) seeds a board from plan files with deps. 🔌

---

## 6. Autonomy & orchestration

| Capability | What it does | File | Status |
|---|---|---|---|
| **Self‑feed driver** | One cheap cycle: read objective → `autonomy_live.run(max_plans=1)` → isolation‑verify → ledger + WhatsApp | `self_feed_runner.py` | ✅ (scheduled task) |
| **Objective/goal loop** | Drives the harness toward an objective; budgets + Rule‑of‑Three | `tools/autonomy_live.py:run` | ✅ |
| **Deterministic conductor** | decide → plan/run/halt; gates Claude output | `tools/autonomy_loop.py:run_once` | ✅ |
| **Planner call (request_spec)** | POST to Claude proxy; 3 retries; returns "" on outage (no silent crash) | `tools/request_spec.py` | ✅ |
| **Plan validator** | Rejects analyst output lacking OUT_DIR/MODULE_NAME/FUNCTIONS/tests | `tools/plan_validator.py` | ✅ |
| **Kanban board** | Durable sqlite task store; pending/in_progress/done/blocked/escalated | `tools/board.py` | ✅ (subset) |
| **DAG / dispatcher / driver** | Dependency ordering + ready‑task dispatch + per‑task drive w/ checkpoint + road_ready DoD | `tools/{dag,dispatcher,driver}.py` | 🔌 |
| **Auto‑decompose** | Analyst splits a big goal into a board of plan‑tasks with deps | `tools/decompose.py` | 🔌 |
| **Rule‑of‑Three** | A task failing 3× (cross‑cycle, persisted) → escalated, loop stops grinding | `autonomy_live.py` | ✅ |
| **Escalate‑to‑human** | Non‑interactive: board `escalated` + ledger + WhatsApp ping | `self_feed_runner.py` | ✅ |
| **git commit / checkpoint** | Plain commit on green; `checkpoint.py` = snapshot/restore on a side ref | `autonomy_live.py`, `tools/checkpoint.py` | ✅ commit / 🔌 checkpoint |

---

## 7. Self‑correction feedback loop (the closing arc — 2026‑06‑29)

The two halves work **in tandem**: when the local implementer fails a gate, the analyst is automatically
re‑invoked to fix the *spec*, not just resample.

- On `ran_failed`, the loop reads the engine's banked `_fn_fails/*.reason.txt` (exact failing test +
  the local model's candidate) and calls **`repair_spec`** → Claude rewrites the plan (tighten the spec,
  pre‑fill hard logic into `HEADER`, split the function, or fix a bad test), then **retries**.
- Escalates **only if repair also fails** (Rule‑of‑Three). Budgeted `max_repairs=2`/cycle so it can't
  grind. `tools/autonomy_live.py:repair_spec / _recent_fail_feedback`. ✅

This is *why* "no escalation to a bigger model" holds while still self‑correcting: the bigger model fixes
the **spec**, the local model still does the **build**.

---

## 8. Safety

| Capability | What it does | File | Status |
|---|---|---|---|
| **safe_write** | Atomic write + `ast.parse` syntax gate + credential/.git/system deny‑list | `tools/safe_write.py` | 🔌 (loop uses raw `open()` — wire this) |
| **checkpoint** | git snapshot/list/restore on `refs/harness/ckpt` without touching HEAD | `tools/checkpoint.py` | 🔌 |

> ⚠️ Gap to close: the live loop bypasses both safety modules (raw `open()` for plans, plain `git
> commit`). Recovery today is ordinary `git revert`. No dangerous‑command/approval layer exists yet.

---

## 9. Compound‑Engineering (CE) integration — the analyst front‑end

CE = the **design/review** front‑end; Lathe = the **deterministic build** spine. They compose. 🧠

| Capability | What it does | Invoke |
|---|---|---|
| **`hreview.py`** | Capped, read‑only CE review over named files via a persona lens; archives to `docs/ce/` | `python hreview.py <lens> <files>` (9 lenses) |
| **`/ce-plan` gap critic** | System‑gap lens; emits explicit **FORKS** + **P0–P3 risk matrix** per milestone | headless `claude -p "/ce-plan…" --permission-mode plan --max-budget-usd N` |
| **Grounding pre‑step** | Cite real `file:symbol` + past learnings before authoring a plan (kills plausible‑but‑wrong specs) | plan‑header `GROUNDING` block |
| **Stage‑5.5 code‑review gate** | After build‑green: CE personas (correctness/security/data/adversarial…) review deployed code | reviewer‑selection matrix → `hreview.py` |
| **Compounding loop** | `ce-compound` writes solved problems to `docs/solutions/`; researcher reads them back | Stage 7 |

---

## 10. PROCESS methodology (Stages 0–7)

Intake & triage → Design council (anti‑echo, info‑asymmetry) → Calibration dry‑run → Synthesis + blind
contrarian + owner gate → SDLC trace (FR/TS/QA‑###) → Plans (GROUNDING+FORKS, gate‑the‑gates golden/mutant
pair) → Engine (local‑first, circuit‑breaker = 3 identical failures) → CE code‑review gate → Live
verification DoD → Retro. Full spec: `projects/*/PROCESS.md`. 🧠

---

## 11. The gap = the roadmap (what the autonomous loop does NOT yet use)

**Now wired (2026‑06‑29):** the self‑feed loop rotates a per‑cycle **focus** (helper → helper → judged →
artifact): `judged` turns on **select‑K** quality judging, `artifact` builds whole **gated files/UI**, and a
**CE review** runs on green artifacts. The CLI exposes the rest as commands (`decompose`, `run`/dispatcher,
`checkpoint`, `metrics`, `plans`, `selftest`, `review` multi‑lens).

**Still not wired into the autonomous loop (roadmap):** H3–H6 behavioral gates *inside* the loop,
skeleton‑fill/skeleton‑complete, per‑function claude routing, INTEGRATION/PRELUDE/RETIRE, road_ready DoD,
and routing the loop's writes through `safe_write` + `checkpoint` (it still uses raw `open()` + plain
`git commit`). These are the remaining v2 wiring.

---

## 12. How an agent (a prior agent) invokes Lathe

a prior agent drives Lathe through `/` slash‑commands (defined alongside this catalog) — e.g. build a plan,
run a gate, request a CE review, check status. Each command maps to one capability above. See
`LATHE_COMMANDS.md` (companion file).
