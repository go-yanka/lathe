# Changelog

All notable changes to Lathe. Dates are absolute. This project ships **no model weights**.

## v2.1.1 — 2026-07-02

Response to independent review v2 (`LATHE_REVIEW_V2.md`). The headline correction:

- **B4 was a phantom in the v2.1.0 *public* artifact — now fixed for real and proven.** The guard was wired
  in the source tree, but the v2.1.0 export dropped `autonomy_live.py`, so the shipped repo still auto-committed
  and still staged `harness.db`. The reviewer was correct about what shipped. Fixed: the complete export now
  includes `autonomy_live.py`, and — per the lesson — a **claim-level end-to-end regression test**
  (`tools/test_b4_autocommit.py`) proves it in a scratch repo: HEAD unchanged unless `LATHE_AUTO_COMMIT=1`, and
  `harness.db` is never staged. **Discipline going forward: a bug is "Fixed" only when an executable repro passes,
  not when the helper unit-passes.**
- **D2:** `test_safe_write.py` is now portable (OS-appropriate system path) — green on Linux, not just Windows.
- **D3:** `lathe review` now lets an explicitly-set `HARNESS_CLAUDE_URL` win over a silent `claude` CLI (CLI
  remains the default only when no URL is configured; `LATHE_REVIEW_USE_CLI` still forces either way).
- **CI now runs the repo's own `test_*.py`** (incl. the B4 e2e), so claim-level regressions turn CI red — the
  gap (D4) that let the B4 phantom through.

## v2.1.0 — 2026-07-01

Response to an independent deep review (7 bugs + a command audit), plus a workflow
overhaul and a real multi-plan demo. **Every fix and feature in this release was built
*through the harness itself*** — the pure logic was authored as gated, pinned plans
(`spine_helpers`, `flow_report`, `checkin_logic`); the spine only wires the I/O.

### Fixed (from the review — B1–B7)
- **B1** — `engine_v2` no longer writes to a placeholder dir when a plan omits `OUT_DIR`; it defaults to the plan's own directory (`resolve_out_dir`). Verified via the reviewer's exact repro.
- **B2** — the registry gate no longer goes RED on a fresh clone: a missing *runtime* DB (`harness.db`) is treated as uninitialized, not divergence (`treat_missing_as_uninitialized`). Unblocks `do`/`auto`/`gate`; `selftest` is 11/11.
- **B3** — `lathe review` no longer hangs without the `claude` CLI: it routes through the pluggable `HARNESS_CLAUDE_URL` analyst (embedding file contents) with a hard timeout; the CLI path is used only when present.
- **B4** — autonomy commits are now **opt-in** (`LATHE_AUTO_COMMIT=1`) and never stage `harness.db`; no more surprise commits to your branch.
- **B5** — the integration line distinguishes "n/a (no INTEGRATION defined)" from a real skip.
- **B6** — run labels + `selftest` reflect the **configured** model (no hardcoded "qwen"/"rig 35B"); docs reconciled (12B default; benchmark run used a 35B — model-agnostic).
- **B7** — the board driver summarizes crashes instead of dumping tracebacks; optional activity-feed noise silenced.

### Added
- **`lathe checkin`** — a gated, leak-safe check-in that extends the pristine model to the remote: refuses unless gates are green, no relics, and not behind the upstream; `--push` runs a secret scan first.
- **Workflow contracts + transparent reports** — `lathe flow <name>` now shows a contract (when / entry / deliverable / definition-of-done) before running; `--run` ends in a transparent per-step report and a **fail-loud `PASS`/`BLOCKED` verdict** (no more false "green").
- **`ledger`** (`examples/ledger/`) — a real multi-plan demo app: 3 ordered plans, 6 gated functions, genuine cross-module composition — a falsifiable answer to "does it scale past one function?".
- **CI** (`.github/workflows/ci.yml`) — offline checks: modules compile, the validator accepts data-plans/rejects code, the pinned demo rebuilds with zero model calls.
- **Config file** — optional `lathe.config.json` (copy from `lathe.config.example.json`) consolidating `analyst`/`implementer` `{url, model}`, `tries`, and `checkin.remote`; precedence env > config > default. Parse/precedence logic is harness-built (`lathe_config`). Any model works for either role — local-implements is the cost-efficient default; higher+higher is a one-line flip. Secrets stay out of the file.

### Changed
- Model story reconciled across README/WHITEPAPER/ARCHITECTURE/BENCHMARK (12B default; model-agnostic).
- Overclaims curbed: the private flagship app is flagged as not-in-this-repo; "gets better as it ages" reframed as design intent.

## v2.0.0 — 2026-07-01
First public cut of the current engine + toolchain (curated, scrubbed export of the internal tree): plan-as-data validator, nonce-authenticated sandbox, content-hash pinning, six QA gates, spec/test-quality linter, ctags repo-map, named workflows, structured run-logs, vendored Compound-Engineering review personas.

## v0.1 — 2026-06-10
Whitepaper + a minimal reference engine + one example. Preserved under the `v0.1` tag.
