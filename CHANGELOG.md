# Changelog

All notable changes to Lathe. Dates are absolute. This project ships **no model weights**.

## v2.2.0 — 2026-07-02

The full enforcement + persona-market release. Every mechanism built THROUGH the harness with an
acceptance test in `review_tests/` (a claim ships only when its test passes).

- **Mechanism #3 — mutation-score threshold** (`LATHE_MUTATION_SCORE`): deterministic AST mutants of the
  ACCEPTED code must be killed by the suite before it may pin — comprehensiveness measured, not assumed.
  Hardened after the harness's own review found it failed OPEN on malformed inputs: an armed gate now
  fails CLOSED.
- **Enforcement scorecard 3/6 -> plus the STRICT umbrella**: strict mode now also forces the mutation
  score (0.5) on top of criteria/ack/stub-proof/change-proof.
- **REPRODUCIBILITY.md** — the two-claims split measured live: pinned rebuilds byte-identical x3 +
  clean-checkout at 0 tokens (guaranteed); regeneration produced byte-DIFFERENT green code (recorded —
  "a lockfile for AI code: the rebuild is deterministic, not the model").
- **Persona market, complete**: catalog -> **143** (12 vendored MIT, 129 fetchable wshobson MIT, 2 refused
  NOASSERTION) with name-weighted matching (7/8 top-3 on the probe suite); **empirical ratings**
  (`lathe agent rate` — probe + independent judge -> 0-10, decider reweights 0.5x..1.5x; proven live);
  **user overrides** (`personas.priority` + `personas.mandatory` in config); **PERSONAS.md** documents the
  exact sources, the decider pipeline, and the controls.
- **SDLC authoring** (`lathe sdlc "<goal>"`): the analyst writes UC->BR->FR->TS with stable IDs and
  traces_to; the harness-built **RTM gate** refuses orphans/dangling refs (one gap-feedback retry, then
  fail loud); emits REQUIREMENTS.md + rtm.json + a CRITERIA block; the new `sdlc` WORKFLOW chains it into
  ack -> STRICT build -> trace -> review. Proven live (21 traced items, gate PASS).
- Ops fixes from the self-review: persona fetch timeouts tightened (8s/3s connect), config overrides
  type-validated, a dead persona market now reports to stderr instead of dying silently.

## v2.1.4 — 2026-07-02

The round-6 review's consolidated fix list (§15), closed with claim-level tests. Every fix's decision
logic was built **through the harness** (implementer: a frontier model this round; the engine is
model-agnostic).

- **D7 (High) — the decider now auto-fetches a needed-but-absent expert and injects its BODY.**
  `review auto` and the planner tap the persona catalog; a non-vendored pick is fetched license-gated
  (harness-built `spawn_candidates`, fail closed) and its full body becomes a review lens (`@<path>`)
  / planner persona block. Fetch I/O consolidated to one canonical module (`tools/persona_spawn.py`).
  Standing regression `tools/test_d7_autospawn.py`; proven live end-to-end.
- **Transitive pin invalidation (V3 §3)** — change function A's spec and dependent B no longer keeps
  its pin (it was verified against the OLD A: stale-but-green). Deps derive from the pinned code; no
  pin-format change; conservative and transitive. E2E: `tools/test_pin_deps_e2e.py`.
- **Test-ack gate (V4 §3 risk 1)** — the analyst's tests were the one ungated artifact. Opt-in
  (`LATHE_TEST_ACK=1`): the engine refuses to build an un-acknowledged test set; `lathe ack <plan>`
  records the ack keyed by a digest of the exact tests, so any rewrite (incl. by the repair loop)
  forces a human re-read.
- **D8 — matcher understands synonyms/stems**: new `expand_words` (deterministic synonym canon + light
  stemming); "authentication bug" / "login credentials" now reach the security persona (both verified
  failing before). Still LLM-independent.
- **D5b — wrong-200 guard**: a reachable analyst returning well-formed junk is now rejected by content
  validation and falls to the next backend instead of becoming a silent junk verdict. **D5a** —
  both-backends-dead fails loud (rc≠0); now covered by `tools/test_analyst_guard_e2e.py`.
- **Docs**: internal residue purged from every public-shipping doc (DOC_CRITIQUE Finding 1); persona
  runtime cache untracked (gitignore anchoring bug).
- Honest note: the gate refused the maintainer's own first D8 spec (a missing synonym + an
  arithmetically-wrong test) — banked failures showed both; spec sharpened; green. The discipline
  applies to the maintainer too.

## v2.1.3 — 2026-07-02

Hardening found by the harness reviewing **its own** recent output (`lathe review auto`, decider-selected lenses).
- **`mcp_safe` CRITICAL + HIGH fixed** (the input guard that protects the MCP tool surface): `is_within_root` used
  `abspath` and could be **escaped by a symlink/junction** inside root → now `realpath` + `commonpath` + `normcase`
  (verified: a real symlink escape returns False); `reject_flags` **failed open** on non-string input → now fails
  closed. Also fixes the drive-root and case-insensitive-filesystem edge cases. Rebuilt through the harness.
- **Windows cp1252 crash fixed**: 5 subprocess captures decoded child output with the OS default and crashed on
  non-cp1252 bytes — all now `encoding="utf-8", errors="replace"` (`lathe.py`, `lathe_mcp.py`, `hrun.py`, `autonomy_live.py`).
- **Decider now fires on review**: `lathe review auto <files>` auto-selects the appropriate reviewer persona(s) for
  the code's domain (correctness+adversarial + specialists like security/reliability); the `code-review`/`bug-fix`
  workflows use it. Thinking-first, everywhere.

## v2.1.2 — 2026-07-02

- **On-demand agent subsystem** (the "load the program" layer): `lathe agent "<need>" [--spawn]` / `lathe agent refill`
  — a catalog of expert personas (vendored + fetchable), a harness-built decider (`agent_router`), a hard license gate
  (permissive only), and a local mirror that stores each source's LICENSE + refreshes-then-falls-back-to-cache.
  LLM-independent (persona = prompt text injected into any endpoint). Decider also injects expert lenses into the
  planner so a **goal auto-selects the thinking experts**.
- **Claude-ecosystem distribution**: an MCP server (`lathe_mcp.py`) exposing `build/verify/gate/review/do` as tools,
  a Claude **skill** (`skills/lathe/SKILL.md`), a **plugin** manifest, and a PyPI packaging scaffold.
- Fixes the earlier export-completeness gap (the class of miss B4 exposed): the full curated set is now shipped.

## v2.1.1 — 2026-07-02

Response to independent review v2 (`LATHE_REVIEW_V2.md`). The headline correction:

- **B4 was a phantom in the v2.1.0 *public* artifact — now fixed for real and proven.** Whatever the internal
  tree contained, what *shipped* in v2.1.0 lacked the guard in `autonomy_live.py`, so the public repo still
  auto-committed and still staged `harness.db`. The reviewer was correct about what shipped. (An earlier note
  attributed this to the export dropping the file; from the public history alone that root cause isn't
  independently verifiable, so we simply own the shipped defect.) Fixed: the complete export now includes
  `autonomy_live.py`, and — per the lesson — a **claim-level end-to-end regression test**
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
