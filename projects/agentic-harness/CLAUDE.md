# Agentic Harness — Project Guide

A **project-agnostic build harness**: give it a spec → it generates tested code with a cheap local model,
gates the output, and pins it for reproducibility. The harness builds *other* projects (a product is one) — and,
as the proof, **builds itself**. This file is auto-loaded on every Claude CLI call the harness makes, so the
model already knows the doctrine and does NOT re-derive it each run (keeps per-run tokens low). It is generic:
nothing here is tied to any single downstream product.

## Build doctrine — two-tier, gated (do not break)
- **Claude = analyst.** Writes specs + tests (per function, per artifact). Invoked via the local Claude-CLI
  proxy. The premium brain is for analyst + review work only — never the bulk implementer.
- **Local model = implementer.** Generates the code from the spec (`openai:local` → llama-server). Cheap,
  fast, gated. **Never hand-edit generated output** — change the plan's spec/scaffold and regenerate.
- **Spec + tests are the source of truth; code is a build output.** Accepted output is test-gated and
  **pinned** (sha256 of spec+tests+model in `.pins.json`) → identical inputs rebuild instantly from cache.
- **One plan = one small, PURE, fully-tested unit** (≥4 asserts, single-pass; no hidden graph/recursion).
  If the local model can't satisfy a spec, **sharpen the spec / shrink the fill region** — don't brute-force.

## Engine + commands (run from `<LATHE_ROOT>`)
- Build a plan:  `python engine_v2.py projects/agentic-harness/plans/<plan>.py openai:local 3`
- Plan modes: **FUNCTIONS** (pure fns gated by tests) · **ARTIFACTS** (files gated by a script; `skeleton`
  for skeleton-complete pages) · **GLUE** (verbatim, no model).
- After a successful build the engine runs **standing regression** (`projects/<proj>/qa/run_gates.py`) and
  **archives** any files the plan declares in `RETIRE = [...]` to `_archive/<date>-<plan>/`.

## Quality + cleanup gates (the discipline that makes it trustworthy)
- **stale_gate** (`qa/stale_gate.py`, in `qa/run_gates.py`): FAILS the build if any backup/dup/superseded
  file lingers in `tools/` or `plans/`. This is what prevents stale artifacts from accumulating and
  confusing later runs (the "many stray files / many DBs" failure mode). Decide-then-archive, never leave junk.
- **CE review gate** (`hreview.py`, PROCESS.md Stage 5.5): `python hreview.py <lens> <files>` runs a
  read-only Compound-Engineering persona review (security / correctness / adversarial / data / perf /
  reliability / api / maintainability / ui). Findings → `docs/ce/`, folded back into the owning plan +
  regenerated. CE never edits code.
- **Failure-as-asset:** failed candidates + the failing test are banked in `tools/_fn_fails/` so the analyst
  sharpens the spec from evidence, not guesses.

## Key paths
- `plans/` analyst plans · `tools/` generated modules · `tools/.pins.json` reproducibility cache ·
  `tools/_fn_fails/` banked failures · `qa/` gates · `_archive/` retired files · `harness.db` (board) ·
  `PROCESS.md` (Stages 0–7 + role checklists) · `docs/` (design + issues).
- Autonomy spine: `tools/autonomy_live.py` (objective → Claude spec → local build → gate → git commit),
  `tools/board.py` / `dispatcher.py` / `driver.py`.

## Environment constraints (host)
- **D: drive is OFF-LIMITS** (loud HDD). Keep all active work on C:.
- **Verify a service is up only from a live probe**, never from logs/memory. The rig LLM returns 503 for
  minutes while loading a 20GB model off HDD — that's loading, not a crash.
- Headless: child processes must not flash console windows (CREATE_NO_WINDOW).

## Provenance & licensing (this is going open-source under Digicraftique.AI)
- The harness stands on open work — **attribute it.** Maintain `NOTICE.md` / `CREDITS.md` listing everything
  borrowed (e.g. llama.cpp for local inference, the Claude Code CLI + Compound-Engineering review personas,
  Playwright for functional gates, axe-core for a11y, bandit for SAST, any model weights and their licenses).
- Keep the harness core free of any downstream product's private code/data. a product-specific logic lives in
  `projects/your-product`, never in the engine. The engine + `projects/agentic-harness` are the publishable parts.
- **Brain is BRING-YOUR-OWN (see `COMPLIANCE.md`).** The high-brain analyst/reviewer is a pluggable endpoint
  (`HARNESS_CLAUDE_URL`, OpenAI-compatible) — users point it at their own Anthropic API key, their own Claude
  CLI, or any other frontier model they have. We use our subscription bridge (`claude_proxy.py`) INTERNALLY
  only; the shipped default routes nobody through our credentials. (Recommend API-key auth in user docs.)
- Every release must be **buildable by the harness itself** (the headline claim: spec → tested code) and
  ship the run-report + gate results as evidence.
