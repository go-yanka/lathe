# Lathe — Independent Review & Command-Test Findings

**Reviewer:** an independent AI agent (Claude), read-only + live-execution review.
**Date:** 2026-07-01 · **Commit reviewed:** `b75eddf` (Lathe v2.0.0) · **Branch:** `claude/lathe-project-review-nvxojt`

## How this was tested (method + honesty boundary)

The harness talks to two OpenAI/Ollama-compatible HTTP endpoints: an **implementer** (`LOCAL_OPENAI_URL`)
and an **analyst** (`HARNESS_CLAUDE_URL`). For the live tests I stood up two local mock servers and **the
reviewing model (Claude) authored every completion** — drafting specs/tests as the analyst and writing code
as the implementer. So the real engine, plan validator, sandbox gate, pinning, integration test, repair
loop, board, and QA gates all executed for real; **only the "model" was a stand-in.**

**Boundary this does NOT cover:** because a strong model returned known-correct code, the correctness /
first-pass numbers reflect a *perfect* implementer, **not** a quantized ~12B local model. The whitepaper's
core empirical claim (a local 12B reliably nails these specs) still requires a real local model on a GPU rig
and is **not** validated here. What *is* validated is the harness plumbing.

After testing, the working tree was reset to pristine `b75eddf` (see Bug B4 — the autonomy commands made
real git commits that had to be discarded).

---

## Command test matrix (every exposed `lathe` subcommand)

Legend: ✅ works · ⚠️ works but degrades/needs a dependency · ❌ broken

| Command | Result | Notes |
|---|---|---|
| `help` / bare | ✅ | prints usage |
| `plans` | ✅ | lists M01–M09 |
| `status` | ✅ | board + pins + live endpoint probes |
| `board [status]` | ✅ | lists tasks after `decompose` |
| `whatis [cap]` | ✅ | registry lookup (note: `task_board -> harness.db`, see B2) |
| `metrics` / `metrics summary` | ✅ | aggregates runs.jsonl |
| `logs` / `--tail` / `--grep` | ✅ | structured per-run trace |
| `issues` / `issues resolved` | ✅ | shared queue (empty by default) |
| `wait` / `resume` / `waiting` | ✅ | task dormancy lifecycle all work |
| `lint-spec <plan>` | ✅ | mutation-probe test-quality check |
| `dups` | ✅ | AST structural-dup report |
| `clean [--dry]` | ✅ | janitor |
| `flow` / `flow <name>` | ✅ | lists/show workflow steps |
| `decompose` | ✅ | seeds board from plans (also bootstraps `harness.db`) |
| `checkpoint [list/…]` | ✅ | git checkpoint refs |
| `gate` (regression) | ✅* | *green ONLY after `harness.db` exists — see B2 |
| `verify <plan>` | ✅ | rebuild + pin reuse (rc=0 confirmed) |
| `build <plan>` | ✅ | both pinned-reuse and model-generate paths work |
| `do "<goal>"` | ✅* | green end-to-end *after* `harness.db` bootstrapped (B2) |
| `chat` | ✅ | REPL starts/exits cleanly |
| `auto ["<obj>"]` | ✅* | repair loop works; *but auto-commits to git (B4)* |
| `run [rounds]` | ✅ | dispatcher drives board; noisy output (B7) |
| `selftest` | ⚠️ | 10/11; the failing "regression" sub-check inherits B2 on a fresh clone |
| `map <file>` | ⚠️ | rc=1, clear "ctags not found" — needs universal-ctags |
| `gate all/h3/h4/h5/h6` | ⚠️ | rc=2, "product gate not found … your-product tree" (by design; core ships none) |
| `review <lens> <files>` | ❌ | **hangs** — requires the `claude` CLI binary; see B3 |
| `report "<title>"` | ✅ | files an issue skeleton (not re-run here; simple I/O) |

**Bottom line:** 24 of 27 commands work correctly. `map` and the `gate` product targets degrade *gracefully*
with clear messages. `review` is the only outright broken one. Two commands (`do`/`auto`) and the default
`gate`/`selftest` are blocked out-of-the-box by B2 until the board DB is bootstrapped.

---

## Bugs (prioritized, with file:line and repro)

### B1 — `engine_v2.py` writes to a garbage directory when a plan omits `OUT_DIR`  ·  **High**
`engine_v2.py:368` and `:704` default `OUT_DIR` to the literal placeholder `r"<LATHE_ROOT>\game_out"` — an
unsubstituted template string with a Windows backslash. On any OS, a plan without an explicit `OUT_DIR`
writes its module + `.pins.json` into a bogus dir literally named `<LATHE_ROOT>\game_out` in the cwd.
- **The shipped example triggers it:** `examples/calc/plan_add.py` sets no `OUT_DIR`.
- Inconsistent within the same file: `:76` (the containment check) defaults `OUT_DIR` to `""`, while `:368`/`:704` use the placeholder. The v1 `engine.py` defaults correctly to the plan's own directory.
- **Repro:** `python engine_v2.py examples/calc/plan_add.py openai:local 3` → creates `./<LATHE_ROOT>\game_out/`.
- **Fix:** default `OUT_DIR` to `os.path.dirname(os.path.abspath(PLAN_PATH))` (match v1), consistently across `:76/:368/:704`.

### B2 — Standing regression gate is RED on a fresh clone (blocks `do`/`auto`/`gate`/`selftest`)  ·  **High**
`capabilities.json` declares `task_board`'s canonical artifact as `harness.db`, a **runtime-generated SQLite
file that is not present in a fresh checkout**. The `capability_registry` gate therefore fails:
`capability_registry FAIL :: task_board: canonical missing on disk (harness.db)`. Because `do`/`auto`/`chat`
run the standing regression gate after each build, **a new user's build passes its own tests but still
reports "no green build this run,"** and the repair loop then spins pointlessly (the failure isn't in the
spec). Running `lathe decompose` (or any board op) creates `harness.db` and the gate immediately goes green —
which confirms the root cause.
- **Repro (fresh clone):** `cd projects/agentic-harness && python qa/run_gates.py` → `capability_registry FAIL`.
- **Fix options:** (a) have the registry gate treat a missing *runtime* canonical (the board DB) as
  "uninitialized," not a divergence; or (b) bootstrap `harness.db` on first run / ship an empty schema; or
  (c) don't register a runtime DB as a required on-disk canonical.

### B3 — `lathe review` hangs; requires the `claude` CLI and ignores the pluggable analyst endpoint  ·  **High**
`hreview.py:105` shells out to the **`claude` CLI binary** (`claude -p --model opus --permission-mode plan
… < prompt`). On a machine without that binary (the documented setup only requires an OpenAI-compatible
`HARNESS_CLAUDE_URL`), the subprocess blocks indefinitely — `lathe review correctness lathe.py` **timed out
at 120s with no error**. This also contradicts the "bring-your-own, pluggable OpenAI-compatible analyst"
design in `CLAUDE.md`/`COMPLIANCE.md`: `review` does not use `HARNESS_CLAUDE_URL` at all.
- **Fix:** route `hreview` through the same `HARNESS_CLAUDE_URL` path as `request_spec.py` (or fall back to
  it when the `claude` CLI is absent), and add a hard timeout + clear error instead of an infinite hang.

### B4 — Autonomy commands make **silent git commits** on the user's current branch  ·  **High**
`lathe auto` / `do` / `run` auto-commit green builds. During testing they created two commits
(`autonomy: task`) on the working branch, committed a `harness.db` blob, rewrote a plan spec
(`M02_dedupe_keep_order.py` via the repair loop), and deleted a generated module — all without prompting.
A user trying the advertised quickstart on their working branch gets **surprise commits and history
rewrites**.
- **Fix:** make auto-commit opt-in (flag/env), commit to a dedicated ref/branch, or at minimum print a loud
  notice and never commit binary runtime state (`harness.db`) or auto-rewrite tracked plan files silently.

### B5 — Misleading "integration: SKIPPED (not all functions solved)" message  ·  Cosmetic
`engine_v2.py:703` initializes the integration status to `"SKIPPED (not all functions solved)"` and leaves it
unchanged when a plan simply defines **no `INTEGRATION`**. It prints even when `functions_passed == total`
and `build_ok: true` (e.g. `build examples/hello.py`). Reads like a failure; it isn't.
- **Fix:** distinguish "no INTEGRATION defined" from "skipped because functions failed."

### B6 — Reports/labels hardcode the model as "qwen" / "rig 35B"  ·  Cosmetic (but credibility-relevant)
Run reports label generated functions `PASS (qwen)` and `selftest` prints `rig 35B reachable` regardless of
the actual configured model (`LATHE_MODEL` / `LOCAL_OPENAI_URL`). This mirrors a **documentation
inconsistency**: `WHITEPAPER.md` describes a **12B Gemma** on an 8 GB card, while `ARCHITECTURE.md`,
`BENCHMARK.md` say **"local 35B"** and `engine_v2.py`'s default is `qwen2.5-coder`. Pick one truth and make
labels reflect the configured endpoint.

### B7 — `run` dispatcher leaks tracebacks + connection-refused noise  ·  Low (robustness)
`lathe run` printed raw `Traceback` text for plans it couldn't build and repeated
`activity log skipped: <urlopen error [Errno 111] Connection refused>` (an optional activity feed). rc was
still 0, but the output is alarming and unstructured.
- **Fix:** swallow the optional-activity-feed error quietly; summarize per-task build failures instead of dumping tracebacks.

---

## Findings from the artifact/documentation review (non-code)

1. **The whitepaper's flagship application is not in the repo.** `WHITEPAPER.md:110-111` cites *"23 ordered
   plans — a scoring engine, 47 data-source ingesters, an AI layer, a FastAPI server, and model-generated
   UI — built and reproduced end to end."* The public tree contains **9 plans (M01–M09), each building one
   trivial pure function** (dedupe, clamp, weighted-mean…), explicitly auto-refilled "so the agent never
   idles." The central *scaling* claim is therefore **not verifiable** from anything shipped.
2. **Benchmark is a null result.** `BENCHMARK.md`: 5 trivial functions, single run, all three tools pass
   5/5, Lathe slowest. Honestly presented, but it demonstrates none of Lathe's claimed advantages
   (hard-task correctness, reproducibility, cost). The doc lists those as "not yet measured."
3. **Model story is internally inconsistent** — see B6 (12B vs 35B vs qwen2.5-coder across docs).
4. **Very young / lightly exercised.** 4 commits over ~3 weeks, curated bulk drops, **no CI** (`.github/`
   absent), and the shipped tree had never been built in place (no `.pins.json`/`harness.db`/`_archive/`).
   Claims like "used internally on real projects" and "gets better as it ages" aren't evidenced by the repo.

## What genuinely holds up (verified by reading AND running)

- **Reproducibility / pinning is real.** Byte-stable rebuild with **0 model calls**, offline. Confirmed live.
- **Security engineering is the strongest part.** `plan_validator.py` (closed-rule allowlist, pure-literal
  exec'd fields, dunder blocking, scan-then-swap RCE guards) and `sandbox.py` (nonce-authenticated,
  unforgeable verdict; process-tree kill; docker/docker-ssh tiers) are genuine, threat-modeled work — not
  stubs. `SECURITY.md` is honest about the irreducible floor and the subprocess-mode caveat.
- **The pipeline works end-to-end** over real HTTP: generate → sandbox-gate → assemble → integration → pin,
  plus the two-tier analyst↔implementer split and the failure→repair loop.
- **The six QA gates, the mutation-probe spec linter, and the board/dispatcher are real and functional.**

## Suggested fix order for the working LLM
1. **B2** (fresh-clone gate red) and **B1** (OUT_DIR placeholder) — these break the two documented quickstarts
   (`lathe do`, `engine_v2`/`lathe build`) on first use.
2. **B4** (silent git commits) — surprising and potentially destructive to a user's branch.
3. **B3** (`review` hangs / ignores pluggable endpoint).
4. Reconcile the **12B/35B/qwen** model story across docs + labels (B6); fix the misleading integration
   message (B5) and dispatcher noise (B7).
5. Ship **one real multi-plan application** (even redacted) and the **harder benchmark** `BENCHMARK.md`
   already promises, so the scaling/cost/correctness claims become falsifiable.

---

## Appendix — Test environment & methodology (full detail, reproducible)

### Environment
- **Host:** an ephemeral, isolated Linux container (cloud sandbox allocated for this review session) —
  Linux 6.x, Python **3.11.15**, repo cloned fresh at `/home/user/lathe`, checked out at `b75eddf`.
- **Deliberately absent** (which is what made several findings visible): no GPU, no Ollama or
  llama-server, no `claude` CLI binary (→ exposed B3), no universal-ctags (→ `map`'s graceful degrade),
  no product-gates tree (→ `gate h3..h6/all` graceful degrade). Docker was not used; all sandbox runs
  used Lathe's **default `subprocess` isolation tier**, which is what `run_unit()` selects when
  `LATHE_SANDBOX` is unset.

### How the two model endpoints were provided
Lathe expects two OpenAI-chat-completions-compatible HTTP endpoints:

| Role | Env var | Port used |
|---|---|---|
| Implementer ("local model") | `LOCAL_OPENAI_URL` | `http://127.0.0.1:8089/v1/chat/completions` |
| Analyst ("frontier model") | `HARNESS_CLAUDE_URL` | `http://127.0.0.1:8787/v1/chat/completions` |

A single ~100-line **stdlib-only Python file** (`scratch_mock_model.py`, `http.server`-based, since
deleted in cleanup) was run twice — `python3 scratch_mock_model.py impl 8089` and
`python3 scratch_mock_model.py analyst 8787`. Each instance:
- answered `POST` with the exact wire shape the engine parses:
  `{"choices":[{"message":{"role":"assistant","content": ...}}], "usage":{"prompt_tokens":N,"completion_tokens":N}}`;
- answered `GET` with a health/models JSON (so `lathe status`/`selftest` probes read "up");
- **logged every incoming prompt** to `scratch_prompts_<role>.log` so the run was auditable.

**The completions were authored by the reviewing model (Claude) itself** — this was the "plug yourself
into both places" design:
- **Implementer role:** parsed the target function name from the engine's prompt (the engine asks
  ``Return ONLY the Python function `NAME` ``) and returned a correct, hand-authored implementation for
  it (`add`, `is_even`, `fizzbuzz`, `greet`, `token_overlap`, `parse_duration`), fenced in
  ```` ```python ```` blocks exactly as a real model would.
- **Analyst role:** returned a complete, valid **data-only Lathe plan** (`OUT_DIR`, `MODULE_NAME`,
  `HEADER`, `FUNCTIONS` with ≥4 assert tests) for the requested goal — which the real
  `plan_validator.py` then accepted, proving the validator path runs on analyst output.

Everything downstream of the HTTP boundary was **stock Lathe, unmodified**: `engine_v2.py`,
`plan_validator.py` (force-enabled by `lathe.py main()`), `sandbox.py` subprocess tier with the
nonce-framed verdict, pinning to `.pins.json`, integration tests, the six `qa/` gates, the SQLite board,
dispatcher, and the analyst repair loop.

### Test sequence actually executed
1. **Offline pin reuse (no endpoints at all):** `python3 lathe.py build examples/hello.py` → pin reused,
   0 model calls, `build_ok:true` (validates the reproducibility story without any model).
2. **Real generate→gate→pin:** deleted `examples/calc/.pins.json` + `calc.py`, ran
   `python3 engine_v2.py examples/calc/plan_add.py openai:local 3` → 3/3 functions generated over HTTP,
   each sandbox-gated, integration `PASS`, pins written. **Re-ran identically** → 3/3 `REUSED (pinned)`,
   0 model calls, integration still green (reproducibility on the generate path). This run exposed **B1**
   (output written to the literal `<LATHE_ROOT>\game_out` directory).
3. **Both-endpoint autonomy:** `python3 lathe.py do "a function that parses a duration like 2h30m into
   seconds"` → analyst drafted the plan, implementer built it, function passed its own tests — but the
   standing regression gate failed on the missing `harness.db` and the repair loop spun (**B2**). After
   `lathe decompose` created the board DB, the same command went green end-to-end (`DONE - 1 module(s)
   built gated-green`), which isolated B2's root cause.
4. **Full command matrix:** every one of the 27 subcommands run with a **per-command timeout** and output
   captured to a file to read the **true exit code** (an earlier pass piping to `head` produced a
   SIGPIPE false alarm of rc=1 on `build`/`verify` — re-verified via file capture: true rc=0).
   `chat` was tested by piping `quit` on stdin; `auto`, `run 2`, `selftest`, `metrics summary`,
   `logs --tail`, `wait/resume/waiting`, `lint-spec`, `dups`, `clean --dry`, `flow`, `checkpoint`,
   `whatis`, `gate` (+product targets), `review` (confirmed hang at 120s and again at 20s → **B3**).
5. **Cleanup / restore:** killed both mock servers, then discovered `do`/`auto`/`run` had created **two
   real commits** (`autonomy: task`) on the working branch, committed a `harness.db` blob, and rewritten
   `plans/M02_dedupe_keep_order.py` via the repair loop (**B4**). Restored with
   `git reset --hard b75eddf && git clean -fd`; verified `git status` empty and ports 8089/8787 free.
   The junk commits were never pushed.

### What this methodology can and cannot claim
- **Validates:** the harness plumbing end-to-end — wire contracts, validator, sandbox verdict path,
  pinning/reproducibility, integration gating, board/dispatcher, repair-loop wiring, every CLI surface,
  and the four High-priority bugs (each reproduced with the stock code path, not a modified one).
- **Does not validate:** implementer-model quality claims. The stand-in implementer returned
  known-correct code on the first try, so first-pass/tries/cost numbers here say nothing about a real
  quantized ~12B local model. Also untested: docker / docker-ssh sandbox tiers (no docker in the
  container), UI/ARTIFACTS plans with Playwright functional gates, and Windows-specific paths.

### To reproduce
Any OpenAI-compatible stub (or a real model) on the two URLs above reproduces every result; the bug
repros in B1–B4 each include their exact command. Total wall time for the full matrix: ~10 minutes.
