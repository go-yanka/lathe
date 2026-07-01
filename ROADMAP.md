# Lathe — Roadmap to "must-use" (closing the external-review gaps)

Goal: knock off **everything** the two external reviews flagged, plus our own deferred fixes — phased,
verifiable, and **dogfooded through the harness** wherever the work is buildable code. Nothing off the table.

## Operating principles
- **Dogfood maximally.** Any pure-function logic (linter scoring, metrics aggregation, gate checks, benchmark
  harness) is built via Lathe *plans* and gated by its own tests. We never hand-write what the harness can build.
- **The harness tests the harness.** Each new capability is exercised by `lathe selftest` + `lathe review`
  (multi-lens) before it lands; the test-quality linter (Phase 1) then improves every build after it.
- **Verify, don't assert.** Every phase has explicit exit criteria proven by a command, not a claim.
- **Vendor-don't-fork.** Fixes land in master → re-cut canonical → projects re-vendor. Spine stays hand-maintained.

---

## Phase 0 — Solidify the base (close the open backlog)  ★ no blockers
Everything already identified but deferred. Build the new pure bits via the harness; spine fixes by hand.
- Engine hardening: atomic writes (`.tmp`+`os.replace`) for module/artifact/itest; pin rollback on regression
  fail; prelude / post-validate-exec **fail-loud** (not silent `continue`); `_judge_best` failure observability
  (print + a `judge_failures` counter in METRICS_JSON); file-lock the `.pins.json` read-modify-write.
- Round-2 publish-blockers: cross-platform issues dir (`~/.lathe/issues`); env-derived status labels;
  `cmd_chat` try/except; planner emits the shared-resource hint unconditionally; `registry_violations`
  superseder-must-be-live + names the colliding capabilities (rebuilt via harness).
- **Exit:** `lathe selftest` 12/12, `lathe gate` 4/4, `lathe review` clean on changed files; re-cut canonical.

## Phase 1 — Test-quality verification (the deepest risk)  ★ no blockers — highest leverage
Review 2's sharpest point: *the engine verifies the contract is MET, not that it is GOOD.* A shallow analyst
test → perfectly-generated wrong code → green gate → poison shipped. Nothing guards this today.
- Build a **spec/test linter** that runs BEFORE the implementer loops and scores the analyst's tests:
  trivial-assertion detection, edge-case coverage (empty/None/0/negative/boundary), mutation-style "would a
  no-op / identity / constant impl pass?" probe, assertion-density, branch coverage of the described behavior.
- Wire it as a pre-implementer gate (warn, then optionally block low-quality specs) + a `lathe lint-spec <plan>`.
- **Dogfood:** the scoring functions are pure → built via Lathe plans, gated by their own tests. Mutation probe
  reuses the existing sandbox.
- **Exit:** demonstrably catches a deliberately-shallow test (e.g. `assert f(1)==1` only) and raises the bar;
  measured on our own plan corpus.

## Phase 1b — Structured logging / observability  ★ no blockers — owner-flagged "definitely do"
Today "logging" = ~120 bare `print()` calls + `runs.jsonl` (metrics) + `RUN_REPORT.md` + `_fn_fails/*.reason.txt`
+ the board. No unified, timestamped, leveled, per-run log. When a project files a bug they paste stdout — the
harness can't hand them a self-diagnosing trace. Gap, especially now that projects file real bugs.
- A real logger: every run gets a `runs/<ts>-<plan>-<runid>.log` (JSONL) capturing each stage (validate, model
  call w/ tokens+latency, gate verdict, pin reuse, repair, retire, regression) at INFO/DEBUG, with a `run_id`
  that also tags the metrics row — so a bug report = "send me `runs/<id>.log`" and it's all there.
- `lathe logs [--run <id>] [--tail] [--grep]`; redact secrets; cap/rotate size.
- **Dogfood:** the log-formatting/redaction/rotation helpers are pure → built via Lathe plans.
- **Exit:** a reproduced bug is fully diagnosable from its run log alone; the issue-queue TEMPLATE asks for it.

## Phase 1c — Documentation: every skill with an example + the architecture explained  ★ no blockers — owner-flagged
Audit found docs are thin on *examples*: `LATHE_COMMANDS.md` 0 runnable examples, `LATHE_CAPABILITIES.md` 0,
`LATHE_GUIDE.md` only 7. Skills are *described* but not *shown*.
- **Per-skill reference:** every command/capability gets a one-paragraph "what + when + why" **and a copy-paste
  runnable example with expected output** (auto-checked against `lathe --help` so docs can't drift).
- **Architecture explainer:** one doc that actually explains the harness logic end-to-end — the two-tier loop,
  plan-as-data + validator, the sandbox/verdict channel, gates, pinning, repair, autonomy — with a diagram and
  "why it's built this way," so a new reader (or skeptic) understands the design, not just the commands.
- **Exit:** a newcomer can learn every skill from one example each, and the architecture from one doc.

## Phase 2 — Execution trust (Docker)  ✅ UNBLOCKED via the rig's Docker over SSH
Both reviews' #1 risk: the engine runs model-written code; `LATHE_SANDBOX=docker` exists but is UNTESTED.
- Local Docker is a dead end here (no admin, virtualization firmware disabled, no WSL distro). **Resolved**
  differently: the **rig runs Docker 29.3.1**, reachable over SSH (`ssh rig`, key-auth, non-interactive OK).
  The daemon is NOT exposed over TCP (good). So the sandbox runs untrusted code **in a container ON THE RIG**
  over SSH — arguably *stronger* isolation (separate machine, not the dev host).
- Work: add a `LATHE_DOCKER_SSH=rig` mode to `sandbox.py` (pipe code+nonce over `ssh rig docker run -i --rm
  --network none --memory ... --pids-limit ...`); threat-model doc; default for untrusted plans;
  `lathe selftest --docker`; a red-team escape plan that must be contained.
- **Exit:** a hostile plan that escapes the in-proc sandbox is contained under docker, proven by a red-team plan.

## Phase 3 — Honest measurement & evidence  ⚠ impediment: benchmark deps + budget
- **Metrics surface:** aggregate `runs.jsonl` → build-success rate, cost/function, first-pass rate, churn over
  time, escalation rate. `lathe metrics --summary`. (Aggregators are pure → built via harness.)
- **Honest benchmarks vs baselines:** a fixed task set built three ways — Lathe, raw Claude (one-shot), Aider —
  compared on pass rate, cost, human-edits-needed. Published with methodology, warts included.
- **Impediment:** needs Aider installed + API budget + an agreed *fair* task set (a biased benchmark is worse
  than none). I'll propose the task set; you approve budget + fairness.
- **Record/replay cassette layer** (accepted from a downstream project issue, 2026-06-30): record `{request-hash ->
  response}` for model calls on first run, replay offline by hash after, re-record via `LATHE_GATE_RECORD=1`;
  plus a saved real-world fixture convention. Makes expensive *nondeterministic* LLM-pipeline e2e invariants
  cheap + deterministic as build gates (the class of bug — a multi-batch off-by-one — that slipped past a tiny
  fixture). Cassette store + hash matching is pure → built via the harness.

## Phase 4 — Non-functional gates  ⚠ minor impediment: tool availability
Add to `run_gates`: a **lint** gate (ruff), a **coverage** gate (coverage.py threshold on generated modules),
a **perf** gate (regression vs a recorded baseline for hot pure fns).
- **Dogfood:** gate logic built via harness where pure.
- **Impediment:** ruff + coverage.py must be installed in the env (pip — I can do this, just flagging).
- **Exit:** all three run in `lathe gate`; a deliberately slow/uncovered/unlinted module fails.

## Phase 5 — Reduce frontier dependence  ⚠ impediment: capable local analyst model
- **Local analyst fallback:** when the Claude proxy is down/over-budget, fall back to a strong local model for
  spec/test authoring; measure the quality delta vs Claude (using Phase 1's linter as the yardstick).
- **Impediment:** spec-writing is harder than implementation; the current rig 35B may be too weak as *analyst*.
  May need a larger local model → hardware/model availability. I'll measure the delta and report whether it's
  viable on current hardware before committing.

## Phase 6 — Prune complexity & curate  ★ no blockers
- Audit the 127-module set: collapse the `*_utils/_extras/_helpers` near-duplicate families, register the real
  capabilities, archive true junk (decide-then-archive, never delete). Make `lathe dups` a **hard gate** option.
- **Exit:** module count justified (every module either registered or clearly distinct); `lathe dups` clean or
  consciously-accepted; tree defensible to a skeptic.

## Phase 7 — Public core + launch readiness  ★ partial blocker: independent users
Review 2's "decouple the core" + Review 1's packaging. This is a **separate product** from the vendoring bundle.
- Carve a clean minimal **public CORE** (engine + validator + sandbox + CLI + core gates + docs), LICENSE,
  README, install script, and a **one-command reproducible demo** (the hands-off legacy-script refactor Review 2
  suggested, not a calculator). Reframe messaging: *disciplined, test-pinned, reproducible* — not "autonomous AI
  engineer." Clear threat-model doc.
- **Independent users (2-3):** ⚠ I cannot recruit real third parties — you bring them; I make onboarding
  frictionless (install + demo + issue queue) and incorporate their findings.
- **Exit:** a skeptic can `git clone` → run the demo in one command → reproduce the numbers; 2-3 outside users
  have run it and filed feedback.

---

## Impediments summary (probed 2026-06-30 — only these need you)
1. ⛔ **Docker NOT installed** (Phase 2 live test). Needs Docker Desktop + WSL2 (admin). I do all code now;
   only the container test waits on this.
2. ⚠ **Benchmark fairness + API budget** (Phase 3) — Aider is pip-installable by me; the *fair task set* and
   *budget* need your sign-off (a biased benchmark is worse than none).
3. ⚠ **A capable local analyst model** (Phase 5) — may exceed current hardware; I'll measure before committing.
4. ⚠ **Independent third-party users** (Phase 7) — you recruit; I remove all friction.
5. ⚠ **API budget headroom** generally — benchmarks + autonomy runs consume Claude.
✅ Cleared: **ruff 0.1.6** and **coverage.py 7.12** are installed → Phase 4 is unblocked and fully unattended.
Everything except the 5 above (Phases 0, 1, 4, 6, the engineering in 2/3/5/7) I finish unattended, dogfooded.

## Sequencing
0 → 1 first (solid base, then the deepest-risk fix that also improves every later build). 2 and 3 in parallel
once 1 lands (Docker is independent; metrics feed benchmarks). 4, 6 anytime. 5 after 3 (needs the yardstick).
7 last (it packages the proven result). I run each phase, verify, report, and re-cut canonical at phase ends.
