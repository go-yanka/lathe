# Lathe v2.62.6 — Deep Audit (harness review + adversarial direct-hunt)

**Method.** Two independent passes, run together so each checks the other.
1. **Through the harness, via the terminal — all review methods, no exceptions:**
   - `lathe review all` (all 10 CE lenses) on the three safety-critical files: `advocate.py`, `engine_v2.py`, `run_gates.py`.
   - `lathe review auto` (the decider picks lenses + auto-spawns experts) on 24 core code + doc targets.
   - `lathe dups` across the whole tree.
   - **Reports (the "croissants") are on disk:** `projects/agentic-harness/docs/ce/review_*.txt` (one per lens) + 27 sweep logs. Analyst = Claude (opus) through the real `claude_proxy.py`; implementer = sonnet.
2. **Adversarial direct read** of the same core, hunting the specific defect classes requested: logic flaws / weak logic, hardcoded values, dead / dangling code, dubious integration joints, and version/count drift — the classes a persona lens under-targets.

Every HIGH below was re-verified against current source with line numbers (not relayed on trust). Confidence tags: **CONFIRMED** (traced in source) vs **PLAUSIBLE** (argued, not fully traced). Source column: `H`=harness lens found it, `D`=direct-hunt found it, `H+D`=both independently.

> **Scope caveat.** `claude_proxy.py` is the **internal subscription bridge** (`CLAUDE.md`: "We use our subscription bridge INTERNALLY only; the shipped default routes nobody through our credentials"). Its "unauthenticated endpoint" findings are **dev-bridge** severity, not shipped-default — but they still matter because the audit drove real analyst traffic through it and the same patterns recur in `lathe_api.py`, which *is* a shipped surface.

---

## 1. Security / guard-bypass — HIGH

| # | Loc | Src | Conf | Defect |
|---|-----|-----|------|--------|
| S1 | `engine_v2.py:411` | D | **CONFIRMED** | `_sandbox()` accepts only `subprocess`/`docker`. `LATHE_SANDBOX=docker-ssh` — a value **advertised** at `env_catalog.py:59` (+`LATHE_DOCKER_SSH` at :62) — hits the `mode not in (...)` branch → `_SB=False` → returns `None` → the **trusted in-process fast path** (line 826). Model/plan code runs **unsandboxed** while the operator believes it's isolated. Directly violates the function's own docstring ("FAILS LOUD… never silently falls through to in-proc — that would be false security"). Fix: accept `docker-ssh`, or drop it from the catalog. |
| S2 | `lathe.py:2029/2148/2487` | H | **CONFIRMED** | `cmd_ack`, `cmd_assume`, `cmd_trace` do `spec.loader.exec_module(plan)` with **no** `_validate_plan_file` — while `cmd_build:171` / `cmd_verify:1258` are gated. `lathe trace evil.py` (or `ack`/`assume`) executes a plan's top-level `import os; os.system(...)` that `lathe build evil.py` would refuse. Guard-consistency hole. Fix: validate before exec on every exec_module path; honor `LATHE_TRUST_PLAN`. |
| S3 | `lathe_mcp.py` (lathe_review branch) | H | PLAUSIBLE | Only `files` is checked with `is_within_root`; `lenses` passes `reject_flags` only, then `cmd_review` re-parses argv positionally — a path smuggled in `lenses` (`/etc/passwd`, `~/.ssh/id_rsa`) becomes a "reviewed file" and is returned to the client. Fix: allowlist lens tokens against the known lens set. |
| S4 | `claude_proxy.py` (`_base_cmd` Read tool) | H | PLAUSIBLE | Any request carrying an `image_url` enables `--allowedTools Read`, not scoped to the image tmp dir; the attacker-controlled prompt can read/return `~/.claude/.credentials.json`, `.env`, SSH keys. Endpoint is unauthenticated. **Dev-bridge severity** (see caveat), but fix: scope reads to `IMG_DIR` via `--add-dir`, require auth. |

---

## 2. Learning-loop / bandit logic flaws — HIGH (the "exploit" half is inert)

The persona explore/exploit bandit is advertised as UCB1 over *verified grades*. In practice the exploit signal never forms. This is the deepest structural finding of the audit — a whole shipped feature that is a silent no-op, with **no error anywhere**.

| # | Loc | Src | Conf | Defect |
|---|-----|-----|------|--------|
| P1 | `persona_spawn.py:127` → `persona_orchestrator.py:151-160,196` | H+D | **CONFIRMED** | The sole caller of `record_run` passes `contributions={}` **every run** → every ledger row written `raised=0, confirmed=0` → `update_grades`'s `if raised and raised>0:` is always false → `grades.json` is **never written** → `load_grades` always returns `{}` → `ucb1(grades.get(name,0.0),…)` always sees mean `0.0` → UCB1 collapses to pure exploration (least-visited). The "explore/exploit over verified grades" never exploits. `finding_score`/`grade_update` are never exercised with real data. |
| P2 | `persona_orchestrator.py:159` | H+D | **CONFIRMED** | `usage_record(…, contrib, contrib, …)` sets `raised` **and** `confirmed` to the same value → the quality ratio `conf = confirmed/raised` is structurally **always 1.0**. Even if P1 were fixed, grades would inflate uniformly and the bandit would rank noise. |
| P3 | `persona_orchestrator.py:record_run` | H | PLAUSIBLE | Every *considered* persona is recorded `fired=True`; `select_live` derives visit counts from `fired`, so never-selected personas accrue `count=N, grade=0.0`, their UCB score shrinks, and they're permanently starved — bandit collapses to rich-get-richer. Fix: record `fired = (name in sel_set)`. |
| P4 | `persona_select.py:7,60` | H+D | **CONFIRMED** | `isinstance(count, bool) or not isinstance(count, int)` → a **float** count (`5.0` from JSON/pandas) scores `inf` → always "unexplored", `total` collapses (`log(1)=0` kills exploration) → selection degrades to a **static alphabetical picker** with no error. Latent today (live path passes ints) but a brittle joint: sibling `grades` are accepted as float while counts must be strict int. |
| P5 | `persona_select.py:28` (`select_personas`) | D | **CONFIRMED (grepped)** | **Dead code** — no live caller (only its own plan/tests). The live decider (`persona_orchestrator.select_live`) re-implements ranking inline and **breaks ties differently**: `select_personas` ties alphabetically (`:69`), `select_live` ties by relevance rank (`:123`). The pin-gated test proves a function that **never runs**; the live tie-break is unguarded and free to drift. |

---

## 3. Gate fail-open / fail-closed inversions — HIGH / MED

| # | Loc | Src | Conf | Defect |
|---|-----|-----|------|--------|
| G1 | `run_gates.py:83-91` | H×5 + D | **CONFIRMED** | Retry loop `break`s the instant **any** attempt returns 0, applied to **every** gate. A real ~1-in-3 race/behavioral defect is reported PASS ~87% of builds and ships green — inverting fail-closed → fail-open for exactly the class the browser/behavioral gates exist to catch. Independently flagged by **5 lenses** (correctness/adversarial/data/reliability/api). Fix: scope any-pass retry to the HEAVY set; deterministic gates single-shot (or require all attempts pass). |
| G2 | `run_gates.py:81,86` | H×6 | **CONFIRMED** | `int(os.environ.get("GATE_RETRIES","2"))` / `GATE_TIMEOUT` parsed with **no** try/except. `GATE_RETRIES=` (empty — common in CI), `off`, or `2.5` → uncaught `ValueError` → the **whole regression** dies → every build spuriously RED on an env typo. `GATE_RETRIES=-1` → `range(0)` → no gate runs → all INOPERATIVE. Fix: parse once defensively + clamp. |
| G3 | `engine_v2.py:1704` | H+D | **CONFIRMED** | Artifact-only (web) plans force `module_ok=False` (1564) → the standing regression/stale gate block is skipped, and `build_ok` (1759) doesn't require it → a **web build ships green having never run the regression gate**, despite the stated intent that the gate covers the webapp lane. |
| G4 | `engine_v2.py` (pin/adopt) | H | PLAUSIBLE | Fail-open pin path: an armed verifier that silently doesn't run + `_adopt_same_class` mis-declaring the regime/version a pin was verified under → un-gated code pins while the manifest reports it fully verified. |
| G5 | `engine_v2.py:build_ok` | H×3 | **CONFIRMED (pattern)** | `build_ok` fails on regression `TIMEOUT` but **not** integration `TIMEOUT` (only `startswith("FAIL")`). A hung GLUE `main()` → `integration="TIMEOUT…"` → `build_ok=True`, module written, exit 0. Fix: add `TIMEOUT` to the integration check. Broader smell: `build_ok` re-derives green/red from free-form string prefixes — reformatting a message silently breaks the decision. |
| G6 | `engine_v2.py` STRICT/TEST-ACK block | H | PLAUSIBLE | `except Exception: pass` around a **present** policy module turns the whole STRICT umbrella into a no-op while the build ships green (the sibling assumption gate correctly fails closed). Fix: narrow except to import/FileNotFound. |
| G7 | `hreview.py:195` | D | **CONFIRMED** | Broad `except Exception` around the wrong-200 guard falls back to `return bool(_t.strip())` — any non-empty text passes as a valid review, defeating the D5b "well-formed-200 must not pass" protection whenever the guard raises internally. Related: `hreview.py` exits **rc 0 on any parseable text regardless of findings** (`:203/208`), so a CRITICAL review reads as a green gate to a caller keying on exit code. |
| G8 | `run_gates.py:104` | H+D | **CONFIRMED** | `_crashed` requires empty stdout **and** literal `"Traceback"` in stderr → a gate that prints one line before crashing, or dies via segfault/`os._exit`/OOM-kill, is mislabeled `FAIL` instead of `INOPERATIVE`, losing the tri-state the design added. (Fails closed — correct — but loses the "couldn't run vs. found a defect" signal.) |

---

## 4. Config / env drift + hardcoded values — MED / LOW

The single-source-of-truth `env_catalog.py` disagrees with real code defaults in several places; the drift gate only catches *missing names*, never *value* mismatches, so these pass silently.

| # | Loc | Src | Conf | Defect |
|---|-----|-----|------|--------|
| C1 | `lathe.py:979` vs `953` | D | **CONFIRMED** | Decider table label `"performance"` (981) ≠ `_ALL_LENSES` token `"perf"` (953); filter at 989 drops it → the **performance lens can never be auto-selected** on `review auto`. Every other cap label matches; only perf is broken. |
| C2 | `engine_v2.py:355` vs `env_catalog.py:19` | D | **CONFIRMED** | `CLAUDE_TIMEOUT` default is `600` in code, `120` in the catalog — a 5× disagreement; `lathe env` reports a wrong number. |
| C3 | `lathe.py:200,1267` | D | **CONFIRMED** | `cmd_verify`'s verdict reader and the auto-repair INOPERATIVE check **hardcode** `ROOT/metrics/runs.jsonl`, ignoring `LATHE_METRICS_PATH` (which the engine writer and `cmd_metrics` both honor) → with the env set, `verify` prints the wrong reproducibility verdict. |
| C4 | `lathe.py:1640,1611` | D | **CONFIRMED** | `selftest` hardcodes `http://127.0.0.1:8787/health` (ignoring `HARNESS_CLAUDE_URL`, which `cmd_status` derives correctly) → false analyst-DOWN for any non-default/remote proxy. Also bakes the plan stem `"M01_token_overlap"`. |
| C5 | `claude_proxy.py:35-39` | D | **CONFIRMED** | Default `CLAUDE_BIN = %APPDATA%\npm\claude.cmd` — a **Windows-only** path; on the documented Linux host every completion fails until `CLAUDE_BIN` is set. (Also `DEFAULT_MODEL`, port `8787` hardcoded but override-able.) |
| C6 | `lathe_mcp.py:87` | H+D | **CONFIRMED** | `serverInfo.version = "2.1.1"` baked literal vs repo `VERSION` 2.62.6 — never sourced from `VERSION`; drifts every release. (Also `lathe_mcp.py:29` tool desc "six standing tree gates" vs ~27 registered.) |
| C7 | `engine_v2.py:21` / `env_catalog.py:13` | D | PLAUSIBLE | `HARNESS_MODEL` default `"gemma4:12b"` — no such model exists (Gemma 2/3 shipped; 12B is `gemma3:12b`); a stale/typo default that would 404 as a fallback. `LATHE_GUIDE.md` also shows `gemma2:12b` at install → three-way disagreement. |
| C8 | `autonomy_live.py:316` | D | **CONFIRMED** | `_CLASS_MODEL = {"frontier":"claude","local-large":"qwen-35B","local-small":"ornith-9b"}` — non-overridable literal model names (unlike the surrounding env-driven `LATHE_MODEL`/`HARNESS_ANALYST_MODEL`); swapping local models means editing source. |
| C9 | `lathe_api.py:46` | H+D | **CONFIRMED** | `_SECRET_HINT` substrings (`api`,`key`,`token`) over-match: the child build's env is stripped of `LATHE_ENGINE_REQUIRE_TOKEN` / `LATHE_SPINE_TOKEN` (and any user analyst `*_KEY`), so an API-triggered build silently runs under **weaker gates** than the operator set — "no gate is weakened" violated, and BYOK auth can be stripped. |
| C10 | `request_spec.py:99` | H+D | **CONFIRMED** | Outbound analyst POST sends only `Content-Type` — **no `Authorization`/`x-api-key`**. Compounded by the SSRF guard (`:36-56`) refusing non-loopback hosts unless `LATHE_TRUST_REMOTE_ANALYST=1`. So the documented "point at your own API key" path is **doubly broken**: blocked by the guard *and* unauthenticated — the user gets a swallowed `""` that reads as "proxy unreachable." |
| C11 | `engine_v2.py:198` | D | PLAUSIBLE | `_advisory = _policy.strip().lower() in (…, "")` — an **explicitly empty** `LATHE_ASSUMPTION_POLICY=""` (easy in a shell wrapper) silently downgrades the assumption gate to advisory instead of falling back to the documented `"high"`. |

---

## 5. Dead / dangling / duplicate code — LOW

| # | Loc | Src | Defect |
|---|-----|-----|--------|
| E1 | `persona_select.py:28` | D | `select_personas` is dead (see P5) — a full public function + its pinned test, never called live. |
| E2 | `lathe.py:939` | D | `runner = os.path.join(PRODUCT_GATES, "run_all.py" if …)` is unconditionally overwritten at 941 — dead assignment, and its `else ""` branch builds a bogus dir path. |
| E3 | `workflows.py` build-from-plan step 2 | H | `"trace {plan}"` — `{plan}` is never bound (every other step uses `{args}`) → bare `lathe build` traces the literal string `"{plan}"` → errors on a nonexistent plan. |
| E4 | `engine_v2.py:1613-1620` | D | On a regression-red build the engine rolls back the `.py` module, pins, and artifacts but **not** the generated `MODULE_NAME.js` — a failed polyglot build leaves a stale, lathe-marked `.js` a later rebuild will honor. |
| E5 | `lathe dups` (advisory) | H | 2 cross-module clones: `persona_orchestrator.{ledger,grades,manifests}_path` ↔ `persona_spawn.ratings_path`; `code_output_utils.extract_test_count_from_plan` ↔ `harness_pipeline_tools.strip_code_fences`. Not blockers; consolidate. |

---

## 6. Cross-cutting design theme — "fail-open safety gates"

Called out independently by the harness (`review data`, adversarial) **and** the direct-hunt: a striking number of *safety* gates degrade **open/silent** on bad or degenerate input, while the *build-blocking* gates (assumption, missing-gate-file) correctly fail closed. Same shape, repeated:

- `run_gates.py` retry masks real intermittent failures (G1); env typo crashes the whole suite (G2).
- `engine_v2.py` STRICT/TEST-ACK `except: pass` no-ops the umbrella (G6); artifact builds skip regression (G3); empty `LATHE_ASSUMPTION_POLICY` → advisory (C11).
- `hreview.py` broad-except passes any text as a valid review (G7).
- `LATHE_MUTATION_SCORE` garbage/out-of-range → gate silently skipped (from CLI_REFERENCE review); empty-mutant functions → vacuous pass.

**Recommendation:** a single `_env_on()` / defensive-parse helper + a rule that a *safety* gate which cannot evaluate its input must fail **closed or INOPERATIVE**, never silently green. This is one design fix, not a dozen nits.

---

## 7. Generated-code corroboration ("gated-green ≠ bug-free")

`review auto`/`all` on the **green generated** modules from the 10-project shakedown independently found real defects the analyst's own tests never covered — reinforcing the earlier meta-finding:
- `wav_header_math.py`: sub-8-bit `bit_depth` silently collapses to `0` (`// 8`), making a real file indistinguishable from empty; float type leakage (`total_frames` returns `250.0`); negative-field sign divergence between duration and frame count.
- (prior wave) `csv_type_infer` quoting/leading-zero loss; `color_palette` `#fff` crash.

The harness's **own review is the mitigation** — it catches these. The gap is that a plain `do` build ships them because the analyst systematically under-covers malformed/boundary input.

---

## 8. Sweep coverage notes (honest gaps in *this* audit)

- 3 `review auto` runs hit the 500s timeout (`engine_v2.py`, `lathe_mcp.py`, `lathe_api.py`) — only some lenses completed. **Full coverage of `engine_v2.py` exists** via the `review all` run; `lathe_mcp.py`/`lathe_api.py` are covered by the direct-hunt. Recommend raising the per-file `review auto` timeout for large files, or the decider chunking them.
- `auto_GATES_REFERENCE_md` BLOCKED — my sweep script pointed at `GATES_REFERENCE.md` (root); the file is at `docs/GATES_REFERENCE.md`. Script path error on my side, not a harness bug — noted so the gap is visible.
- One recovered analyst rejection (advocate `ui` lens, wrong-200 guard fired → fell through to next analyst → "no material findings"). Working as designed.

---

## Route-first (my read)

1. **S1 docker-ssh unsandboxed** + **S2 exec_module guard bypass** — the two confirmed isolation/guard holes.
2. **G1 retry-masking + G2 env-crash** — the standing regression is defeated both ways.
3. **P1/P2 bandit exploit-signal dead** — a shipped learning feature is a silent no-op.
4. **G3 web builds skip regression** + **G5 integration-TIMEOUT ships green**.
5. **C1 perf lens dead**, **C6 MCP version**, **C9/C10 auth-strip + BYOK** — quick, high-signal drift/joint fixes.

All findings are for the maintainer/implementer to triage and fix in the owning plans (harness doctrine: fix upstream in the plan, never hand-edit generated code).
