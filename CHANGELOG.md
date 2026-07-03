# Changelog

All notable changes to Lathe. Dates are absolute. This project ships **no model weights**.

## v2.6.1 — 2026-07-02

**`--accept-all` as an explicit opt-in** (owner refinement): bulk accept is useful, but must be a deliberate
choice, never the default. `lathe assume <plan> --resolve --accept-all` accepts every blocker as-stated
without individual review; the audit trail records each honestly as "accepted in bulk (not individually
reviewed)", so the record shows it was the user's call. Default stays per-item (nothing auto-accepted).

## v2.6.0 — 2026-07-02

**Assumption gate: resolve, don't rubber-stamp** (owner directive — "speculation brings noise; never let
assumptions be silently validated; throw each back to the user to confirm, choose, or state their intent").
The confirm flow was a weak ack (and a `--yes` blanket-accept); it's now a real per-item resolution:
- **`--yes` blanket-accept removed.** `lathe assume <plan> --resolve` (alias `--confirm`) throws each blocking
  assumption back and requires an explicit decision: **accept** as the real intent, **pick** an alternative
  the auditor offered (`[options: …]`), or **type what you actually want**. Skipping leaves it blocking
  (fail-safe). `--answers <file>` gives one decision per blocker for CI — still per-item, never a blanket.
- **Every resolution is a recorded decision** (with its method: accepted / chose / stated) written to a
  **committed** `<plan>.decisions.md` audit trail — a resolved assumption is now a *stated decision*, not a
  silent guess. (`.assumptions.json` remains the per-environment machine cache; `ASSUMPTIONS.md` retired.)
- The `assumption-auditor` persona may now offer alternative resolutions inline (`[options: …]`), reusing the
  liaison's option format, so the user can pick instead of typing.
- Verified end-to-end with the real auditor: audit → per-item resolve (no blanket) → committed decisions.md →
  STRICT build with `LATHE_ASSUMPTION_GATE` active passed. Acceptance test rewritten accordingly.

## v2.5.1 — 2026-07-02

**Docs completeness for the assumption gate + dogfood proof.** Swept *every* narrative doc so the assumption
gate is reflected consistently: LATHE_GUIDE (seven gates + `lathe assume` in the CLI table), PERSONAS (new
"purpose-built workflow personas" section documenting `requirements-liaison` **and** `assumption-auditor` —
previously the persona doc covered neither), README (`sdlc` row now shows the assumption-audit step),
WHITEPAPER (strict-rigor paragraph now names the adversarial auditor + user-governed scrutiny). No code change.
- **Dogfood verified end-to-end with the *real* auditor** (not the mock): `lathe assume` on the assumption
  plan itself surfaced 7 real unstated assumptions (4 HIGH) in its own spec; after confirming them the full
  `LATHE_STRICT=1` build ran with `LATHE_ASSUMPTION_GATE=1` **active** and passed. The block-when-unconfirmed
  path was separately proven (engine refuses pre-generation). `ASSUMPTIONS.md` gitignored (per-audit artifact).

## v2.5.0 — 2026-07-02

**Assumption gate — surface the LLM's silent guesses before they ship** (owner idea). The known failure
mode: hand a model an underspecified goal and it doesn't stop — it fills every gap with a "reasonable
default" and proceeds ("intent drift"); worse, told to ask when unsure, it rates its own guesses as "common
enough" and skips (documented in the literature — see the whitepaper/README references). So Lathe now runs an
**adversarial `assumption-auditor` persona** that re-reads a spec *against the goal* and emits a
materiality-ranked ledger of the decisions the goal never specified, and a gate that **refuses to build while
any HIGH-materiality assumption is unconfirmed**.
- New command `lathe assume <plan>` (audit → `ASSUMPTIONS.md` + `.assumptions.json`) and `--confirm` (walk the
  blockers). Confirmations keyed to a spec digest — any spec change re-opens the audit.
- **Scrutiny is user-governed** (owner refinement): `--scrutiny` / `LATHE_ASSUMPTION_POLICY` / config
  `assumptions.scrutiny`, levels `all` › `high+med` › **`high` (default)** › `off`/`advisory`. A team can dial
  the gate down to `off` (ledger still emitted, build not blocked) without abandoning STRICT, or up to `all`.
- New gate `LATHE_ASSUMPTION_GATE=1`, **added to the STRICT umbrella** (now seven composed gates). Runs both
  at `clarify` (advisory — the auditor's findings are appended to `CLARIFIED_GOAL.md`) and pre-build (enforced).
- New pinned pure module `assumption_logic.py` (`parse_assumptions`, `blocking_assumptions`,
  `unconfirmed_blockers`, `spec_digest`) built THROUGH the harness under STRICT — CRITERIA A1–A4, fable
  implementer, all first-try; `strict_mode` rebuilt to include the new key (CRITERIA S1–S2).
- New persona `ce_personas/assumption-auditor.md`; `sdlc`/`enhancement`/`bug-fix` workflows gained an explicit
  assumption-audit step; acceptance test `review_tests/test_assumption_gate.py` (units + audit e2e + confirm
  + the real engine-gate decision, incl. spec-change re-open). Engine-gate refusal verified end-to-end.
- Honest scope: a tripwire against *silent* intent-drift, not a proof of full intent capture — the auditor
  catches what it catches, materiality is a heuristic, and only HIGH blocks (to avoid confirmation fatigue).

## v2.4.0 — 2026-07-02

**Requirements liaison now offers options to pick from** (owner idea). Interrogation was open-questions-only;
now, when a clarifying question has a small bounded answer space, the liaison attaches selectable options with
a recommended default — `Which format? [options: CSV | JSON | TSV] (default: CSV)`. In `lathe clarify` you
answer with the option's number (or Enter for the default); free-text is always allowed; genuinely
open-ended questions stay open. Lower friction, and it surfaces choices the user hadn't considered.
- New pure function `parse_options` (in `clarify_logic`) extracts the options + default from a question line;
  built through the harness under `LATHE_STRICT` (criteria + ack + mutation ≥0.5 + regression + test-kind),
  fable as implementer, first-try pass; the other two clarify functions rebuilt byte-identical from pins.
- `requirements-liaison` persona + the question prompt updated to emit the option markup; `cmd_clarify`
  renders the numbered menu and resolves a numeric pick / empty-for-default / free-text answer.
- Acceptance test extended (`review_tests/test_clarify.py`): parse_options units + an e2e proving a numeric
  pick resolves to the option text and an empty answer resolves to the default (the raw index is never
  recorded as the answer). Plan now declares `CRITERIA` (C1/C2/C3) — `lathe trace` shows 3/3 covered.

## v2.3.1 — 2026-07-02

**Docs sync.** The narrative docs now reflect the shipped capabilities of v2.1.4–v2.3.0 (the enforcement
stack was live in code but under-documented outside README/LATHE_COMMANDS): ARCHITECTURE gained an
*enforcement layer* section (the six gates + `LATHE_STRICT`) and a *thinking-first* section (clarify →
decide → sdlc); LATHE_CAPABILITIES gained enforcement-stack rows with an honest-scope note (these bound
*test quality per gated function*, not whole-program correctness); FOR_PROJECTS gained the STRICT one-switch
and the clarify-liaison items; LATHE_GUIDE gained clarify/sdlc/ack/trace/agent CLI rows. WHITEPAPER was
brought into canonical (it had been public-only) with an honest-scope sentence on strict rigor. No code
change. (Public FOR_PROJECTS keeps its `127.0.0.1` scrub — the rig LAN IP is never exported.)

## v2.3.0 — 2026-07-02

**Requirements liaison — interrogate for clarity before the harness thinks** (owner idea). A goal handed to
an LLM with hidden ambiguity produces confidently-wrong code; now there's a step that drags the ambiguity
out with the user, up front.
- `lathe clarify "<goal>"`: a **requirements-liaison persona** (`ce_personas/requirements-liaison.md`) asks
  the fewest, sharpest clarifying questions (inputs/outputs/success criteria/constraints/edge cases/
  non-goals), you answer (interactive or `--answers` file), and it writes `CLARIFIED_GOAL.md` — a refined
  goal + assumptions + **testable acceptance criteria** + non-goals + open questions — to feed `do`/`sdlc`.
- A goal that already states inputs+outputs is passed through (no busywork). It's now **step 0 of the
  `sdlc` workflow**. Pure logic harness-built (`tools/clarify_logic.py` — goal_vagueness + parse_questions);
  acceptance `review_tests/test_clarify.py` ALL PASS; proven live (Fable asked 5 real questions, synthesized
  the brief, and honestly refused to invent answers when the scripted answers were offset).

## v2.2.4 — 2026-07-02

Enforcement mechanism **#5 — required KIND of test per contract**. This completes the reviewer's 6/6 stack.
- A function may declare `'kinds': ['property', 'edge', ...]` (or the plan a default `TEST_KINDS`); under
  `LATHE_TEST_KIND=1` (forced by STRICT) a unit whose tests don't contain its declared kinds is **refused**,
  before any generation. Kinds (property / roundtrip / edge / error / example) are detected structurally,
  no model call (`tools/test_kind.py`). The `enhancement` workflow now asks for a property test per invariant.
- Acceptance `review_tests/test_test_kind.py` ALL PASS; STRICT composes it alongside the other five.
- Persona buckets: attempted a token-aware refinement, it regressed (over-matched `language`) and my tests
  were too weak to catch it — reverted to the better substring bucketer. Buckets remain heuristic/advisory.

## v2.2.3 — 2026-07-02

Enforcement mechanism **#6 — gate the glue** (the last honest gap), plus a doc-integrity fix.
- **Gate the glue** (`LATHE_GATE_GLUE=1`, forced by STRICT): `GLUE` — the architect's hand-written wiring,
  the most bug-prone part — must be exercised by an `INTEGRATION` test or the build is refused (substantive
  glue only, > `LATHE_GLUE_MAX` lines). Harness-built (`tools/glue_gate.py`); acceptance
  `review_tests/test_glue_gate.py` ALL PASS. This closes the "function, not anything" qualifier: under
  STRICT, **no code ships untested**, not just no function.
- **README recovery**: a read-after-truncate bug in the v2.2.1 doc script (`open("w").write(open().read())`
  truncates before the read) shipped an **empty README for v2.2.1–v2.2.2**. Restored from history and
  re-applied every change since; the mutation-score scope clause and the glue-gate bullet are now in place.
- STRICT now composes #6 alongside criteria/ack/regression-proof/lint/mutation-score.

## v2.2.2 — 2026-07-02

Persona library governance (owner directive: get the expert library right).
- **Buckets** — all 143 agents tagged with a when-to-invoke bucket (`persona_market.bucket_of`); browse
  with `lathe agent bucket`. Advisory heuristic.
- **CE floor** — the decider now guarantees at least one Compound-Engineering reviewer in every selection
  (review always runs correctness+adversarial; the planner floors correctness-reviewer). Governance rule.
- **Your default agents** — `personas.mandatory` (1-2 names in every call), and the shipped config boosts
  the CE reviewers' priority by default.
- **Batch grading** — `lathe agent rate --all [N]`: grade every agent (field probe + independent judge →
  0-10), resumable, feeds the decider's rating factor.

## v2.2.1 — 2026-07-02

Adversarial edge-case pass on the v2.2.0 mutation gate (independent review §16, E1–E4) — all four
reproduced and fixed, each with an acceptance test in `review_tests/`.

- **E2 (High) — equivalent mutants no longer falsely block correct code.** A mutant no input can
  distinguish from the accepted code (e.g. slack in a guard constant) is unkillable; counting it made a
  *complete* suite score < threshold. New deterministic differential probe (`tools/mutation_equiv.py`)
  excludes provably-equivalent mutants from the denominator. Verified: the reviewer's `scale` repro builds
  green; a genuinely weak `square` suite still blocks.
- **E1 (Med-High) — the gate no longer fails OPEN on "no mutants".** Operators broadened (boolean and/or,
  `not`-drop, `in`/`is`, string constants) so string/collection/boolean leaf functions are actually
  measured; a function with no mutable nodes is reported `unmeasurable` (ledger flag + loud warning), not
  silently passed.
- **E3 (Med) — STRICT no longer silently ignores ARTIFACTS-only plans**: it now refuses them with an
  explicit "cannot gate an ARTIFACTS-only plan" message (wording matches code; the #6 glue gap is stated,
  not hidden).
- **E4 (Low-Med) — regression-proof rename bypass closed**: a fix that renames the changed function is
  matched against the disappeared old def and still refused if it ships no reproducing test.
- **Docs**: the mutation-score scope is now stated honestly wherever comprehensiveness is claimed — a
  bounded tripwire for vacuous tests, not exhaustive mutation coverage.

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
