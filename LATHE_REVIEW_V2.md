# Lathe — Independent Review v2: Full Re-Analysis of v2.1.0

**Reviewer:** an AI agent (Claude), acting as tester **and** as the stand-in for both model endpoints **and**
as the analyst in the harness-review passes. **Circularity disclosure (read this first):** no result in this
review was produced or checked by a model other than the reviewer. Where a check is genuinely model-*independent*
— git HEAD comparison (B4), deterministic string guards (MCP injection refusals), offline pinned rebuilds
(zero model calls), the security battery, and anything verified against git/file state — it is trustworthy on
its own terms. Where a result is model-*contingent* — every "green" end-to-end build, because my stand-in
implementer returns correct code on the first try — it demonstrates only that the *plumbing runs when fed
flawless completions*, not that a real cheap model would pass. The harness's own `lathe review` passes are
also Claude reading Claude: an adversarial second pass with real value (it caught genuine defects, below), but
not an *independent* oracle. Treat "verified" in this document as "checked against non-model evidence" only
where that evidence is named; elsewhere read it as "the reviewer's reasoning, uncorroborated by a second party."
**Date:** 2026-07-02 · **Commit reviewed:** `ca4d8d1` (v2.1.0) · previous review: `b75eddf` (v2.0.0), see `LATHE_REVIEW_FINDINGS.md`.
**Test system:** `review_tests/` (in this repo) — reusable, one command: `python review_tests/run_all.py`.
⚠️ **This command mutates git:** the B4 phase runs `lathe auto`, which on a repo where the bug is unfixed
(e.g. v2.1.0) creates real `autonomy: task` commits (and stages `harness.db`). It resets afterward, but run
it on a scratch branch/clone; if it aborts mid-run, `git reset --hard` to your prior HEAD. (Fix noted in §13.)

---

> ## Round-3 update — v2.1.2 (`2a4bd67`), 2026-07-02
>
> The author shipped two more releases (v2.1.1, v2.1.2) responding to this review. **I re-audited against
> `2a4bd67` with the same test system and direct repros. The single red — B4 — is now genuinely fixed
> (confirmed by git-HEAD comparison, a model-*independent* check), and all 6 sweep phases are GREEN (the
> CLI+workflow matrix, the largest single phase, is 46/46 — that number is that phase's count, not the whole
> sweep; other phases report their own: battery 34/34, unit 9/9 groups, repo tests 10/10, etc.).**
> *Caveat, stated up front: the matrix's 46/46 counts plumbing that runs correctly when my stand-in implementer feeds it
> perfect code; it does **not** test whether a real cheap local model would pass — that core claim remains
> unproven in anything shipped (see §4 model-contingency split).* Details in **§12** (appended). Headlines:
> - **B4 fixed and proven — author's *root-cause story* contradicted by git.** The fix is real; the
>   changelog's explanation is not. It says "the v2.1.0 export dropped `autonomy_live.py`," but
>   `git show ca4d8d1:...autonomy_live.py` shows the file **shipped, just unguarded** (exactly my v2 finding).
>   What was missing was the guard *wiring*, not the file. The fix itself is verified two independent ways:
>   their `tools/test_b4_autocommit.py` passes all 4 cases, and my own git-HEAD repro independently confirms
>   all three states — `lathe auto` leaves HEAD untouched at unset **and** `=0`, moves it only at `=1`
>   (`60a421a→dadc2e2`, reset after), never stages `harness.db` (now gitignored too).
>   Full detail and why the pattern matters: §12a.
> - **D2, D3 fixed and verified** — Linux test now portable (repo's own suite is green on Linux); `review`
>   now lets an explicit `HARNESS_CLAUDE_URL` win with CLI fallback on *any* non-usable response.
> - **CI now runs the repo's own `test_*.py`** (incl. the B4 e2e) — closing the D4 gap that let the phantom
>   through in the first place.
> - **New in v2.1.2:** an agent subsystem and an **MCP server** (`lathe_mcp.py`) — Phase-2 of this review's
>   roadmap, shipped. I tested it live (JSON-RPC init/list/call + two injection attacks); it works and its
>   input guards hold. The B4 episode's discipline ("a bug is fixed only when an executable repro passes")
>   is now stated in the changelog as policy. **The body of this review below describes v2.1.0; §12 is the
>   current state.**

## TL;DR verdict

Lathe v2.1.0 is a **substantially improved, largely honest, genuinely working harness** whose author
responded to independent review faster and more completely than most established projects would —
**6 of the 7 reported bugs are verifiably fixed**, the overclaims were retracted in plain language, CI was
added, and a real multi-plan demo now makes the composition claim falsifiable.

Two blunt truths temper this:

1. **One "fixed" bug is a phantom (B4).** The fix function was spec'd, generated, test-gated, pinned —
   and **never wired into the code path it was supposed to gate**. `lathe auto` still silently commits to
   your git branch, and the changelog's claim that it no longer stages `harness.db` is also false. This is
   a textbook instance of the exact failure mode Lathe's own doctrine says it prevents: the *function* is
   gated green, but nothing gates the *integration*, and the docs drifted from reality on day one.
2. **The core empirical claim remains untested at its intended scale.** The harness plumbing is now solid;
   whether a quantized ~12B local model can really carry the implementer role on non-toy work is still
   undemonstrated in anything shipped.

On the market question: five independent research sweeps (sources cited in §8) found that Lathe's exact
combination — per-function spec+test data files, a hard sandbox test gate as the acceptance condition,
content-hash-pinned byte-identical rebuilds, no-hand-edit discipline, refuse-to-escalate, local-first —
**is offered by no shipping tool**, while the *category* around it (spec-driven development) has explosive,
verified demand. There is a real place for this project — narrow today, plausibly widening through 2027 —
if it survives its two structural risks (single-maintainer bus factor and category absorption by
Spec Kit/Kiro/Tessl).

---

## 1. Method (and its honesty boundary)

Per the review protocol, the latest `main` was pulled (`b75eddf` → `ca4d8d1`, three releases) and the
entire analysis was redone against it with a purpose-built, reusable test system committed at
`review_tests/`:

| Component | What it does |
|---|---|
| `mock_models.py` | Dual-role OpenAI-compatible HTTP server; **the reviewing model authors every completion** (implementer on :8089, analyst on :8787), every prompt logged |
| `battery_security.py` | 34 adversarial cases across the plan validator (24), sandbox (8), and spec-lint mutation probe (2)* |
| `unit_functions.py` | Direct unit tests of every pure toolchain function + the generated ledger modules (9 groups) |
| `cli_matrix.py` | All 27+ CLI commands, all 5 workflows, and the exact B1–B7 repros from review v1 (46 checks) |
| `run_all.py` | Orchestrator: 6 phases incl. the repo's own tests, the ledger offline rebuild, and the CI steps run locally |

*counted by assertions executed; see the files for the case lists.*

**What this validates:** the harness — validator, sandbox verdict path, pinning, gates, board, dispatcher,
repair loop, CLI, workflows. **What it cannot validate:** implementer-model quality. The stand-in
implementer returns correct code on the first try, so pass rates say nothing about a real local 12B.
Docker sandbox tiers and Playwright UI gates were untestable in this container (no docker; no display).

---

## 2. The author's response to review v1 — fix verification

Every fix was re-tested with the original repro. The fixes themselves were built *through the harness*
(plans `B_fixes_spine_helpers.py` etc. → generated, gated, pinned modules) — a credible dogfooding claim
that is verifiable in the tree.

| Bug (from v1) | Claimed | Verified | Evidence |
|---|---|---|---|
| B1 — OUT_DIR placeholder dir | Fixed | ✅ **HOLDS** | calc plan builds into its own dir; no `<LATHE_ROOT>\game_out` created; `resolve_out_dir` wired at `engine_v2.py:76,369,706` |
| B2 — gate red on fresh clone | Fixed | ✅ **HOLDS** | registry gate green with `harness.db` absent; `treat_missing_as_uninitialized` wired in `registry.py:46,58`; `selftest` now 11/11 |
| B3 — `review` hangs w/o claude CLI | Fixed | ✅ **HOLDS** (with a nuance) | with no CLI (or `LATHE_REVIEW_USE_CLI=0`) review routes through `HARNESS_CLAUDE_URL` and completed rc=0 in seconds. Nuance: when a `claude` CLI **is** present it is preferred silently even if you configured the URL endpoint — see D3 |
| B4 — silent git commits by autonomy | Fixed | ❌ **PHANTOM** | see §3 — gate function exists but has **no call site**; `lathe auto` moved HEAD in both sweep runs; `harness.db` is still explicitly staged (`autonomy_live.py:281`) |
| B5 — misleading integration label | Fixed | ✅ **HOLDS** | `n/a (no INTEGRATION defined)` printed; `integration_label` wired at `engine_v2.py:705` |
| B6 — hardcoded "qwen"/"35B" labels | Fixed | ✅ **HOLDS** | run reports say `PASS (local)`; selftest labels the configured model; docs reconciled (verified in diffs) |
| B7 — dispatcher tracebacks | Fixed | ✅ **HOLDS** | no raw tracebacks in `lathe run` output; `summarize_failure` wired in `driver.py:34` |

Also verified from v2.0.1's "curb overclaims" commit: the whitepaper now explicitly flags the flagship
app as private/unverifiable from this repo, and "gets better as it ages" was reframed as design intent —
both edits are real and worded honestly.

## 3. The B4 phantom — the most instructive finding in this review

The evidence chain, fully reproducible:

1. `plans/B_fixes_spine_helpers.py:36-47` specs `should_auto_commit(env_value)` with 7 tests.
2. `tools/spine_helpers.py:25` contains the generated, gated, pinned implementation. It passes all its
   tests (my `unit_functions.py` re-verifies it).
3. `grep -rn should_auto_commit` across the repo: **the only references are the plan, the generated
   module, and the changelog/docs.** No caller exists.
4. `autonomy_live.py:276-292` — `commit()` is unguarded, and line 281 stages `harness.db` by name,
   directly contradicting `CHANGELOG.md:16` ("never stage harness.db").
5. Empirically: `lathe auto` with `LATHE_AUTO_COMMIT` unset created 4 commits (`autonomy: task`) on the
   working branch during each sweep. (They were reset away after testing.)

Why this matters more than an ordinary bug: **Lathe's whole thesis is that gates make LLM output
trustworthy.** Here the LLM author produced a gated-green function, an updated changelog, an updated env-var
table in the guide — and no wiring. Every artifact *around* the fix exists; the fix doesn't. The harness's
gates (function tests, six tree gates, docs-drift gate) all passed because none of them checks that a
claimed behavior is actually reachable. The doctrine says "docs can't drift"; the docs drifted. The lesson
for the roadmap is concrete: **claims need end-to-end tests, not just units** — e.g., a regression test
that runs `lathe auto` in a scratch repo and asserts HEAD is unchanged unless `LATHE_AUTO_COMMIT=1`.

## 4. Full test-system results (v2.1.0)

| Phase | Result | Detail |
|---|---|---|
| Security battery — validator | ✅ 24/24 *(against the enumerated classes only)* | accepts 4 legitimate plan shapes; rejects all 20 escape classes (imports, dunders, getattr, f-string/concat non-literals, tuple-unpack & subscript scan-then-swap, bytes tests, `dict()` smuggling, traversal names, untested functions, `types`, `attrgetter`…). **Caveat (harness-flagged): I authored these cases *and* judge them — adversary = oracle — so "24/24" proves the validator blocks the 24 attacks I imagined, not that it is secure. Coverage is bounded by my threat model; an independent auditor with a different one is exactly what's absent.** |
| Security battery — sandbox | ✅ 8/8 | honest pass/fail; hang killed in ~6s; **forged nonce-less verdict rejected**; `os._exit` fails closed; `SystemExit` contained; stdout spam harmless |
| Security battery — spec-lint | ✅ 2/2 | stub-satisfiable tests flagged; strong tests pass the mutation probe |
| Unit tests — toolchain + ledger | ✅ 9/9 groups | incl. all five v2.1.0 fix helpers, config precedence, board/DAG dependency flow, and the generated ledger modules |
| Repo's own tests | ⚠️ 9/10 | `test_safe_write.py` **fails on Linux** (asserts Windows `C:\…` paths are denied; they aren't on POSIX) — defect D2 |
| Ledger multi-plan rebuild | ✅ 3/3 plans | offline, pinned, zero model calls; cross-module composition (`ledger` imports `ledger_core`+`ledger_stats`) verified by direct unit test |
| CI steps (run locally) | ✅ 3/3 | parse-all, validator accept/reject, offline pinned rebuild |
| CLI + workflows matrix | ⚠️ 45/46 | every command works or degrades gracefully; all 5 workflows show contracts and fail-loud verdicts; `flow --run` without a target is BLOCKED (no false green); **the single red is B4** |
| End-to-end `lathe do` | ✅ | analyst(me) → plan → validator → implementer(me) → sandbox gate → pin → green, in one shot |
| `lathe checkin` (new) | ✅ | correctly refused: reported gate/relic/behind-remote blockers with remediation |
| `selftest` | ✅ 11/11 | was 10/11 on a fresh clone in v2.0.0 |

**Reproducibility of these numbers:** the phases split into **model-independent** checks (the security
battery, unit tests, ledger pinned rebuild, CI steps, and every pinned/offline path — these reproduce
byte-for-byte for anyone) and **model-contingent** checks (the end-to-end `do`/`auto`/build greens, which
depend on the implementer behind :8089 one-shotting each task, as this run's stand-in did). A third party
reproducing with a weaker implementer will see the gate hold candidates red and the repair loop engage
rather than instant greens — that is the harness working, not the tests failing, but the headline 45/46
should be read with that split in mind.

**New defects found in v2.1.0 (all minor except D1):**
- **D1 (High):** B4 phantom fix — §3. Autonomy still commits silently; changelog claim false.
- **D2 (Medium):** `test_safe_write.py` fails on Linux — the repo's own test suite is red out of the box
  on the OS its CI runs on (the new CI only compiles/validates/rebuilds; it doesn't run these tests —
  which is why it stays green).
- **D3 (Low/design):** `lathe review` silently prefers the `claude` CLI whenever one exists on PATH, even
  if the user configured `HARNESS_CLAUDE_URL` (`hreview.py:106`, default `LATHE_REVIEW_USE_CLI=1`).
  Least-surprise says an explicitly configured endpoint should win.
- **D4 (Observation):** the harness's gates verify functions and tree hygiene but nothing verifies
  *claims* (see §3). The docs-drift gate checks that commands are documented, not that documentation is true.

## 5. Documentation-claims audit

| Claim | Status at v2.0.0 | Status at v2.1.0 |
|---|---|---|
| "12B on an 8GB GPU" vs "35B" contradiction | Contradictory across 4 docs | ✅ Reconciled ("local model", model-agnostic; changelog discloses the benchmark used a 35B) |
| Flagship 23-plan private app | Presented as proof of scaling | ✅ Flagged as private/unverifiable, public demo promised — and `examples/ledger/` now exists (3 plans, 6 functions, real cross-module imports, integration test). Honest but modest: it proves *composition works*, not *scale* |
| "Gets better as it ages" | Asserted as fact | ✅ Reframed as design intent |
| "Every fix built through the harness itself" | — | ✅ Verifiable in-tree (plans → pinned modules) and credible; but see §3 for what the harness didn't catch |
| CHANGELOG B4 entry | — | ❌ **False on both halves** (not opt-in; still stages `harness.db`) |
| BENCHMARK.md | Honest null result | Unchanged (still 5 trivial tasks; the promised harder benchmark hasn't landed) |

The documentation culture is genuinely above-average in honesty — overclaims were retracted in explicit,
almost self-flagellating language — but the B4 changelog entry shows the failure mode is *unverified
claims*, not dishonesty.

## 6. Functionality — what demonstrably works now

Verified end-to-end in this review: the plan validator (closed-rule, all probed escape classes rejected) ·
the nonce-authenticated sandbox verdict (unforgeable under every forgery attempted) · content-hash pinning
with byte-stable offline rebuilds · the six standing tree gates · spec-quality mutation probing ·
the two-tier analyst/implementer split over plain OpenAI-compatible HTTP · the repair loop (exercised in
review v1, where v2.0.0's red gate drove `spec_repaired` cycles; **not** re-exercised in the v2.1.0 sweep,
where the stand-in implementer never fails — a gap the harness's own reviewer caught, see Appendix) · the SQLite
board, DAG scheduling, dispatcher and dormancy (wait/resume) · all five named workflows with up-front
contracts and fail-loud verdicts · structured per-run logs and honest metrics · the gated `checkin` ·
config-file precedence · CI. That is a **complete, working implementation of the design** — with the
single exception documented in §3.

## 7. Usefulness and real potential

**Who this genuinely serves today:**
- Developers generating **well-scoped pure functions/modules** who want provable correctness and free
  regeneration — especially on private code where cloud tools are unacceptable (the privacy pull is real:
  81% of surveyed developers worry about AI-tool data handling).
- Anyone who needs **AI-generated code to be reproducible** — a property literally no mainstream tool
  offers (§8).
- As a **reference architecture**: the validator/sandbox/pinning trio is publishable-quality security
  engineering that other harness builders could vendor or imitate.

**Where it will frustrate:**
- The unit of work is a single function with assert-string tests. Real backends (I/O, state, async,
  frameworks) don't decompose that cleanly; `GLUE` is hand-written; the analyst does the decomposition,
  and decomposition quality *is* the product. This is the same "sledgehammer for a nut" critique the
  community levels at spec-driven tools generally.
- Writing per-function specs+tests is real work. Lathe converts "review the AI's code" into "specify
  precisely up front" — a trade many developers will refuse (and the "a spec precise enough to determine
  code *is* code" objection applies at this granularity more than any other).
- Single-maintainer project, no community, no packaging (not on PyPI), Windows-first residue in places
  (D2 is exactly that).

**The technical bet is independently supported.** The clearest external evidence found: small models score
~88% on scoped function synthesis (HumanEval, Qwen2.5-Coder-7B) yet **8–16%** on open-ended repo editing
(Aider polyglot, even at 32B). Decomposing to fully-specified single functions moves the task into the
regime where cheap local models are strong — Lathe's core design converts exactly the capability that
small models have into exactly the guarantee (test-gated, pinned) that users lack. A 2026 study (TDAD)
independently found verification structure beats model scale for small-model codegen.

## 8. Market comparison — is anyone already doing this?

Summary of five research sweeps (2025–26 landscape; sources in the reports, key ones linked here).
**Disclosure (harness-flagged), same standard as the byline:** the quantitative figures below (star counts,
funding, survey percentages, regulatory dates, the "68% don't run" and insurance-exclusion claims) are
**reviewer web-research, model-gathered and not independently re-verified** here — except the GitHub star
count, which I checked live via the API. Treat them as directional order-of-magnitude evidence, not audited
fact; a decision-maker should re-confirm any figure they lean on.

**Spec-driven development is now a mass-market category — without Lathe's mechanics.** (All third-party
figures in this section are point-in-time, as of 2026-07-02, and will rot; treat them as order-of-magnitude.)
GitHub **Spec Kit**: 117k stars in 10 months (verified via GitHub API, 2026-07-02) — feature-level Markdown specs,
TDD by *prompt instruction*, no gate, no pinning. AWS **Kiro**: GA Nov 2025, 100k+ waitlist, EARS
acceptance criteria + spec-derived property testing — advisory verification, cloud-only, no pinning.
**Tessl** ($125M raised, ~$500-750M valuation): the closest philosophical neighbor — spec-as-source,
"GENERATED FROM SPEC - DO NOT EDIT" headers — but file-level, JS-only, closed beta, and its own reviewers
flag **non-deterministic regeneration** as the thesis-breaking gap. That named gap is precisely what
Lathe's content-hash pinning answers.

**Coding agents run tests as behavior; none gate on them.** Across Aider, Cline, Cursor, Claude Code,
Codex, Copilot's coding agent, Devin, OpenHands: test loops are repair behavior, not acceptance
conditions (Aider even auto-commits *before* tests run). No surveyed product offers reproducible
regeneration. All escalate to bigger models as the remedy; none refuses. The nearest thing to a hard gate
anywhere is Claude Code's opt-in Stop-hooks.

**Test-gated generation has one dormant near-miss.** BuilderIO's Micro Agent (generate test → iterate
until pass) is the only shipped product with Lathe's acceptance semantics — unmaintained since Nov 2024,
single-file, unsandboxed. Industrial hard-gating exists inside Meta (TestGen-LLM/ACH) but gates *tests*,
not implementations. Sandbox infrastructure itself is now commodity (E2B ~15M runs/month) — the sandbox
isn't the moat; using its verdict as the acceptance function is.

**Model-tiering is crowded in the wrong direction.** FrugalGPT/RouteLLM/Martian and three code-cascade
papers all use verification signals to decide *when to escalate*. "Refuse to escalate, sharpen the spec"
appears to be an unclaimed position.

**Reproducibility demand is latent but the tailwind is real.** Nobody ships content-hash pinning of
generated code (nearest analogues: lockfiles for agent *skills*; Nix for environments). Meanwhile: EU CRA
SBOM deadlines (2026-27), emerging AIBOM procurement asks, insurers introducing generative-AI exclusions
(ISO CG 40 47/48) — and a 68%-of-AI-projects-don't-even-run reproducibility literature. Byte-identical
rebuild is currently a feature nobody asks for by name, answering an objection everybody makes.

**Positioning grid (per-function specs / hard test gate / hash-pinned rebuilds / no-hand-edit /
local-first / refuse-to-escalate):** Spec Kit 0/6 · Kiro 1/6 · Tessl 2/6 · Aider 1/6 · Micro Agent
(dormant) 2/6 · **Lathe 6/6**. The combination is genuinely unoccupied.

## 9. So is there a real place for this? — the verdict

**Yes — a real but specific one.** Three honest scenarios:

1. **As a product for the mainstream developer: unlikely as-is.** The spec-writing tax, single-function
   granularity, and the absence of ecosystem (one maintainer, no PyPI, no community) put it far behind
   Spec Kit/Kiro-class distribution. The benchmark that would justify the machinery (hard tasks where
   one-shots fail; cost curves on real local hardware) still hasn't been run.
2. **As the reference implementation of an unoccupied idea: strong.** Verified-unoccupied combination,
   independently-corroborated technical bet, working code, honest docs, MIT license. If spec-as-source is
   where the industry is heading (Tessl's $125M says investors think so), the deterministic-regeneration
   gap is *the* acknowledged hole in that thesis, and Lathe holds a working answer today. The most likely
   good outcomes are: its mechanisms get absorbed (pinning/gating land in a bigger tool), or it becomes
   the kernel of a niche compliance/provenance play as CRA-era requirements harden through 2027.
3. **As infrastructure for privacy-bound teams (the niche that pays):** local-first + gated + reproducible
   is a real, present-day fit for air-gapped/regulated environments — a segment big enough to sustain a
   serious open-source project, and one where the incumbents (all cloud-first) don't compete.

**Bottom line, unspun:** v2.1.0 upgraded Lathe from "impressive pitch ahead of its evidence" to "working,
honest, security-serious harness with one embarrassing unwired fix and an untested headline bet." The idea
has a defensible, currently-unoccupied position; the project's risks are now mostly *non-technical* —
distribution, maintenance, and whether the author closes the claim-verification gap their own B4 episode
exposed.

## 10. Prioritized recommendations

1. **Wire B4 for real** — guard `commit()` with
   `should_auto_commit(os.environ.get("LATHE_AUTO_COMMIT", "0"))`. The function's string semantics are
   verified, not assumed: it parses against the closed truthy set `{'1','true','yes','on'}`, and both the
   spec's tests (plan lines 41–47) and this review's `unit_functions.py` assert `"1"`/`"TRUE"`/`" yes "`
   → True and `"0"`/`"no"`/`""`/`None` → False — so `LATHE_AUTO_COMMIT=0` disables, and the `"0"` default
   is safe. Drop `harness.db` from `_paths`, and add an end-to-end regression test (scratch repo, run
   `auto`, assert HEAD unchanged **both** with the variable unset and with `LATHE_AUTO_COMMIT=0`).
   Correct the changelog entry.
2. **Fix `test_safe_write.py` portability** (platform-conditional assertions) so the suite is green on
   Linux — this must precede #3.
3. **Add claim-level tests to CI** — run the repo's own `test_*.py` in CI (they'd have caught D2; enabling
   them before fixing #2 would turn CI red), and for every changelog "Fixed" entry, one executable repro.
4. **Prefer explicit config in `review`** (D3): use `HARNESS_CLAUDE_URL` when the user set it, with the
   `claude` CLI as fallback on any **non-usable response** — connection failure, non-2xx status, or a
   malformed/empty completion — not just connection failure (a stale-but-reachable proxy returning 200
   with garbage must also trigger the fallback, or `review` silently produces junk verdicts).
5. **Run the promised harder benchmark** — hard tasks + rebuild axis + metered cost on real local
   hardware. This is the single highest-leverage piece of missing evidence for the whole thesis.
6. **Ship distribution basics** — PyPI packaging, a 5-minute Ollama quickstart, and grow the ledger demo
   toward something with I/O and state to probe the granularity ceiling honestly.

---

## 11. Path to mainstream — what the funded tools have that Lathe doesn't, and what to build

This section answers the strategic question directly: **what would it take for Lathe to compete at or
above the level of the funded players?** It is split into (a) an honest inventory of what they have that
Lathe lacks, (b) what Lathe has that they lack (the assets to build on), and (c) a sequenced roadmap.

### 11a. What they have that Lathe doesn't (the real gaps)

| Gap | Who has it | Where Lathe is today |
|---|---|---|
| **Zero-friction install & onboarding** | Spec Kit (`uvx specify`), Kiro (installer), Cursor (app), Cline (marketplace) | clone a repo, set env vars, run raw `python lathe.py` — not even on PyPI |
| **IDE / editor presence** | Kiro and Cursor *are* IDEs; Copilot/Cline live in VS Code | CLI only; no extension, no MCP server |
| **Works with the agents people already use** | Spec Kit drives 30+ agents; Tessl hooks agents via MCP | Lathe requires its own loop end-to-end |
| **Polyglot output** | all of them (TS/JS/Go/Java/…) | Python-only plans, assert-string tests, Python sandbox |
| **Brownfield support** | Kiro/OpenSpec ("built for brownfield"), every agent edits existing repos | greenfield-only: plans generate new modules; no path to adopt existing code |
| **Feature-level ergonomics** | Kiro: prompt → requirements/design/tasks; Spec Kit: guided phases | the human (or analyst) must already think in single functions; the spec-writing tax is fully exposed |
| **Natural-language authoring UX** | conversational spec refinement, diagrams, review UIs | `lathe do "<goal>"` is one-shot; plan editing is raw Python-file editing |
| **Team & enterprise machinery** | seats, SSO, dashboards, cloud execution, support contracts | none |
| **Ecosystem & registry** | Tessl's Spec Registry (10k+ specs); Spec Kit templates; plugin marketplaces | none |
| **Distribution & community** | 117k stars (Spec Kit), AWS's funnel (Kiro), $125M (Tessl) | single maintainer, no PyPI, no Discord, no docs site |
| **Capital & staffing** | AWS, GitHub, $125M, $2B ARR (Cursor) | one person + a harness |

Two of these deserve emphasis because they are *product* gaps, not resource gaps: **brownfield adoption**
(nobody adopts a tool that can't touch their existing code) and **granularity ergonomics** (competitors
let users think in features; Lathe makes them think in functions). Those two, more than money, explain why
a Spec Kit user wouldn't switch today.

### 11b. What Lathe has that none of them have (the assets)

Verified unoccupied in §8, restated as product assets: (1) the **hard acceptance gate** — the market's
loudest documented pain is "almost-right AI code" and review burden (46% of surveyed developers actively
distrust AI output; the slop crisis); everyone else treats tests as behavior, Lathe treats them as
*acceptance*. (2) **Content-hash pinning / byte-identical rebuilds** — the named, conceded flaw of the
spec-as-source category (Tessl's "non-deterministic compiler" problem); Lathe holds the only working
answer. (3) **Per-function granularity** — the one regime where cheap local models are empirically strong.
(4) **Local-first economics + privacy** — every funded competitor is cloud-first; air-gapped/regulated
teams are structurally underserved. (5) **Provenance by construction** — every accepted function already
has spec+tests+model+hash; that is an AI-BOM waiting to be serialized.

### 11c. Roadmap — sequenced, each phase falsifiable

**Phase 0 — Credibility floor (weeks, no new design).** Fix B4 for real; fix the Linux test failure,
*then* make CI run the repo's own tests (this order — per §10 — or CI turns red on D2 the moment the suite
is enabled); publish to PyPI (`pipx install lathe`); a 5-minute Ollama quickstart
(`lathe init` wizard: detect Ollama, write `lathe.config.json`, build a demo plan); a docs site. *Nothing
else matters until a stranger can succeed in 5 minutes — the funnel today is: clone → read 19 MDs → set
env vars → maybe green.*

**Phase 1 — Reach (the two product gaps).**
- **Polyglot gate.** Keep plans as data; add per-language runners (pytest → jest/vitest → `go test`),
  starting with TypeScript (the largest spec-driven audience, and Tessl's only language). The validator
  and pinning are language-agnostic already; the sandbox needs a runner abstraction.
- **Brownfield adoption: `lathe adopt <file.py::func>`.** Reverse-derive a plan from existing code
  (analyst writes the spec+tests *from* the implementation, human reviews, current code is pinned as-is).
  This converts "rewrite your world" into "adopt one function at a time" — the single highest-leverage
  feature for mainstream adoption, and no competitor has an equivalent of "bring existing code under a
  reproducibility pin."
- **Feature→function compiler.** Let users write a Kiro/Spec-Kit-style feature spec; the analyst
  decomposes it into an ordered set of function plans plus an integration contract, which the human
  approves before any build. This hides the spec-writing tax behind the granularity that makes the whole
  thesis work — and it's exactly the "decomposition is the frontier model's real job" claim
  operationalized.

**Phase 2 — Ride the ecosystem instead of fighting it.**
- **Ship Lathe as an MCP server** (`lathe-mcp`: `draft_plan`, `build`, `verify`, `pins`, `gate`). Claude
  Code, Cursor, Copilot, and Kiro users then get gate+pin+provenance *inside the agent they already use* —
  Lathe becomes the build system under any agent, the way make sits under any editor. This flips every
  competitor from rival to distribution channel, and it is the correct answer to "how do you beat tools
  with 100× your funding": don't out-agent them — be the layer they can't offer (deterministic,
  provenance-grade acceptance) and that costs them nothing to adopt.
- **Spec Kit bridge**: compile a `spec-kit` feature directory into Lathe plans (`lathe import speckit`),
  so the 117k-star funnel feeds Lathe rather than competing with it.

**Phase 3 — Deepen the moats (the "bigger than them" play).**
- **Provenance/attestation as a first-class artifact.** Serialize what pinning already knows into a signed
  AI-BOM per module (spec hash, test hashes, model id, sandbox verdict, timestamp) in in-toto/SLSA style.
  EU CRA deadlines (Sept 2026 / Dec 2027), AIBOM procurement asks, and generative-AI insurance exclusions
  are creating buyers who must *prove* which code is AI-written and how it was verified. **No shipping
  tool can produce this today; Lathe already computes every field.** This is the plausible enterprise
  wedge — and the thing a Tessl or Kiro would eventually pay for or clone.
- **Test-quality escalation: from mutation probe to full mutation + property-based testing.** The
  strongest academic attack on test-gating is "weak tests give false assurance." Lathe already has the
  seed (spec-lint's stub probe). Extending to real mutation scoring and Hypothesis-generated property
  tests at function granularity would make the gate *provably* strong — and pre-empt Kiro's PBT push at
  coarser granularity.
- **Remote pin cache.** Pins are a build cache; add a shared/team pin store (a la Bazel remote cache) and
  a team gets organization-wide reproducibility: one person's gated-green function is everyone's instant,
  verified build. This is the first genuinely *team-shaped* feature and a natural paid tier.
- **The evidence engine.** Publish the harder benchmark (hard tasks where one-shots fail; rebuild axis;
  metered $ on real local hardware vs Aider/Cursor/Copilot), continuously in CI, with a public dashboard.
  For a trust product, the benchmark *is* the marketing.

**Phase 4 — Category claim.** The concept is already being independently reinvented ("VSDD" on HN;
"Compiled AI" on arXiv). Name the category — *deterministic AI builds* / *a lockfile for AI code* — write
the definitive post, and launch where the spec-driven audience already argues (HN thrice-burned by
spec-kit/Kiro threads). First-mover naming matters more than usual here because the mechanism is easy to
describe and hard to retrofit (auto-committing agents can't honestly claim "code is a build output").

### 11d. What money buys that features don't — an honest note

Parity with Kiro/Cursor on *distribution* (IDE polish, cloud fleets, enterprise sales) is not reachable by
feature work; it requires a team and capital, or a home inside a larger project/foundation. The realistic
"as big or bigger" outcomes are: (a) **become the standard layer** — the MCP/agent-substrate route, where
Lathe's mechanisms ship inside everyone else's tools (biggest reach, least revenue); (b) **own the
compliance niche** — provenance-grade AI codegen for regulated/air-gapped buyers (smallest reach, clearest
revenue, defensible against the incumbents' cloud-first DNA); or (c) **be acquired/absorbed** by a
category leader that needs determinism (Tessl's conceded gap is an acquisition thesis in plain sight).
Trying to out-Cursor Cursor is the one strategy the evidence rules out.

**Sequencing discipline:** Phases 0–1 are prerequisites for any of it; the B4 episode shows the
claim-verification culture must harden *before* the surface area grows.

---

## 12. Round-3 re-audit — v2.1.2 (`2a4bd67`)

Same protocol as §1: pulled the new `main` (three releases past the reviewed commit: v2.1.0 → v2.1.1 →
v2.1.2), re-ran the `review_tests/` system, and verified each fix claim with a direct repro. **Result: the
all 6 sweep phases are GREEN and the B4 red from §4 is closed. (Precisely: the CLI+workflow matrix phase is
46/46; the other phases report their own totals — see §12b. "46/46" is that one phase's count, not a
whole-sweep denominator — a distinction the harness's own reviewer rightly forced, since conflating them
would be the very green-label-drift this review flags in Lathe.)**

### 12a. Fix verification (the three open v2 defects + D1/B4)

| Item | v2.1.0 status | v2.1.2 | How I verified |
|---|---|---|---|
| **B4 / D1** — silent autonomy commits | ❌ phantom (unwired) | ✅ **FIXED & PROVEN** (fix, not the story) | `autonomy_live.py:277` now guards `commit()` with `should_auto_commit(...)` and drops `harness.db` from staged paths. **My own git-HEAD repro across all three states:** `lathe auto` **unset → HEAD unchanged**, `=0 → HEAD unchanged` (these two are genuinely *model-independent* — no commit occurs regardless of implementer output), `=1 → HEAD moved` (`60a421a→dadc2e2` in my run; this branch is *model-contingent* — it requires the implementer to succeed enough to reach `commit()`, so it proves "the guard permits a commit," not more). The author's `tools/test_b4_autocommit.py` is a **separate** scratch-repo run (different hashes) that corroborates the *behavior* and adds the "`harness.db` absent from the real commit" assertion. `harness.db` is now gitignored. **But see 12a-note: the changelog's root-cause is false.** |
| **D2** — `test_safe_write.py` red on Linux | ❌ | ✅ **FIXED** | OS-conditional system path (`/etc/hosts` on POSIX); repo's own suite now green on Linux (repo_own_tests phase GREEN, was RED) |
| **D3** — `review` ignores configured URL | ⚠️ design | ✅ **FIXED** | `hreview.py:156-163` orders analyst methods by explicit config: `HARNESS_CLAUDE_URL` set → endpoint first, CLI fallback; fallback now triggers on **any** non-usable response (connection error, non-2xx, empty completion) — matching this review's own Rec #4 |
| **D4** — CI didn't run claim-level tests | ⚠️ | ✅ **FIXED** | CI now runs the repo's `test_*.py` incl. the B4 e2e, so a regression turns CI red — closing the exact gap that let the phantom ship |

**12a-note — the fix is solid; the changelog's root-cause is not, and I initially took it on faith.** My
first draft of this section praised the author's "export gap" explanation as "the most credible thing in
the release." The harness's own adversarial reviewer flagged that I'd exempted that narrative from the
falsifiability standard §3 demands — and it was right. Checking git: `git show
ca4d8d1:projects/agentic-harness/tools/autonomy_live.py` shows the file was **present** at v2.1.0 and
**unguarded** (no `should_auto_commit`; `harness.db` in the staged paths) — precisely my v2 B4 finding. So
the changelog claim "the v2.1.0 export dropped `autonomy_live.py`" is **contradicted by the shipped tree**:
the file shipped; the *guard wiring inside it* did not. Whether that gap was an export-tooling artifact
(private tree had the guard, export shipped a stale copy) or the wiring simply hadn't been written in the
public tree is **unverifiable from outside** — and I should not have vouched for either. What is verifiable,
and what matters: the *fix* in v2.1.2 is real (repro above), and the executable claim-level test now guards
against recurrence. Credit the fix and the test discipline; do **not** credit an unverifiable origin story.
(This correction is itself the §3 lesson applied to the reviewer: a narrative isn't "credible" because it's
plausible and self-flattering to accept — it's credible when the artifacts support it. Here they don't.)

### 12b. Full sweep result (v2.1.2)

| Phase | v2.1.0 | v2.1.2 |
|---|---|---|
| battery_security (34 cases) | ✅ | ✅ |
| unit_functions | ✅ | ✅ |
| repo's own tests | ⚠️ 9/10 (D2) | ✅ **all green** |
| ledger offline rebuild | ✅ | ✅ |
| CI steps local | ✅ | ✅ |
| CLI + workflow matrix | ⚠️ 45/46 (B4) | ✅ **46/46** |
| **Overall** | RED (1 defect) | ✅ **all 6 phases GREEN** — but read the two caveats below |

**Caveat 1 — "46/46" is one phase's count, not the sweep total (harness-flagged; it's the exact
label-drift this review indicts in Lathe).** 46/46 is the **CLI+workflow matrix** phase only. The full run
is 6 phases with their own denominators (battery 34/34, unit 9/9 groups, repo tests 10/10, ledger 3/3, CI
3/3, matrix 46/46). Do not attach "46/46" to the word "sweep" — say "matrix 46/46; all 6 phases green."
**Caveat 2 — the green is model-contingent.** Only a handful of checks are model-*independent* (the B4
git-HEAD repro's negative branches, the offline pinned rebuild, the deterministic security guards); the
end-to-end greens are **contingent on my stand-in implementer returning perfect code on the first try**. So
"green" means "the plumbing runs when fed flawless completions," **not** "a real cheap local model passes."
The honest split: *plumbing verified; implementer-quality thesis still untested in anything shipped.*

**Open items surfaced by the harness's review passes (folded in for honesty).** The round-4 *persona*
critique (correctness + adversarial personas) sharpened my earlier D5 into two distinct cases — my original
framing wrongly lumped a *usable-looking 200* with a *rejected* response, and wrongly claimed the D3 fix
"matches Rec #4." Corrected:
- **D5a (Low/design):** on the both-backends-dead path — `HARNESS_CLAUDE_URL` set, endpoint returns
  **non-2xx / empty / connection error**, **and** no `claude` CLI — the URL is correctly rejected as
  non-usable, fallback to CLI, CLI absent. This path isn't specified/tested; it should **fail loud** with
  "no usable analyst backend" and rc≠0, and be added to the matrix.
- **D5b / Rec #4 correction (Medium):** a **well-formed, non-empty, semantically-wrong 200** is **not
  detectable** by the D3 fix's trigger set (connection / non-2xx / empty completion) — it passes all three,
  is *accepted*, and yields a **silent junk verdict**. So my earlier claim that the D3 fix "matches Rec #4"
  is **wrong**: Rec #4 demanded fallback on exactly this garbage-200 case, and no content-blind check can
  provide it. Honest statement: the fix covers connection/non-2xx/empty failures; the semantically-wrong-200
  case is **unresolved** and needs schema/content validation or a second-opinion oracle — a real limitation,
  not a closed item.
- **D6 (Low):** `should_auto_commit`'s accepted enable-tokens are the closed set `{1,true,yes,on}`; a user
  who writes `LATHE_AUTO_COMMIT=enabled` or `=2` gets silent *disable*. Direction is safe (fails closed),
  but a warn-log on an unrecognized non-empty value would prevent a mis-enabled user believing commits are on.

Also verified beyond the standing sweep: the new **agent subsystem** (`agents/test_agent_system.py`) —
all pass, incl. a compliance gate that refuses unlicensed sources and a fallback that refuses to fabricate
when a source is unreachable and uncached (good failure-closed behavior).

### 12c. New in v2.1.2 — the MCP server (Phase 2 of §11, shipped)

`lathe_mcp.py` exposes `lathe_build/verify/gate/review/do` as MCP tools over stdio JSON-RPC — exactly the
"be the build layer under any agent" route this review recommended (§11c Phase 2) as the highest-leverage
path to reach without out-spending the incumbents. I tested it live end-to-end:

- `initialize` → OK; `tools/list` → the 5 tools; `tools/call lathe_verify` on the pinned demo → returned
  `REUSED (pinned)` (the gate/pin path runs correctly under MCP).
- **Adversarial:** a path-traversal argument (`../../etc/passwd`) and a flag-injection argument
  (`--help lathe.py`) were both **refused** by the harness-built guards (`mcp_safe.py`: `is_within_root`,
  `reject_flags`). The security instinct that made the validator/sandbox strong is present in the new
  surface too.

Also shipped this round, matching §11 Phase 0/2: `pyproject.toml` (PyPI packaging, `lathe-harness`), a
Claude Code **skill** (`skills/lathe/SKILL.md`) and **plugin** manifest, and an `.mcp.json`. The skill's
own framing now uses the category name this review suggested — "deterministic AI builds."

### 12d. Round-3 verdict

**This is the strongest evidence yet in favor of the project — not because the code got bigger, but because
the *process* held under a second adversarial cycle.** The one genuinely damning finding from review v2
(a fix claimed but not shipped) was reproduced by the author, root-caused honestly (an export gap, not a
cover-up), fixed, and locked with a regression test and a CI change that prevents the whole *class* of
"claimed-but-unwired" from recurring. Every other v2 defect is closed and independently re-verified. The
MCP server means Lathe's differentiators (hard gate, pinning, provenance) can now ride inside the agents
people already use — the single most important strategic move available to it.

What has **not** changed, and remains the real work (still open from §7/§9/§11): the core empirical
claim — a cheap local model carrying the implementer role on non-toy tasks — is still unproven in anything
shipped (my tests still use a strong stand-in behind :8089; §4's model-contingency caveat stands); the
harder benchmark (§10 Rec #5) hasn't landed; and distribution/community/team features are still Phase 0-1
ambitions, not reality. The trajectory, though, is now a track record rather than a promise: two review
cycles, both closed with executable proof. If the next milestone is the benchmark (§10 Rec #5) run on real
local hardware, the last big unverified claim closes too.

---

## 14. Publish-readiness — should this go out for general public consumption?

The verdict splits by what "publish" means. **Publishing the open-source repo/idea publicly: yes, now.
Promoting it to a broad general audience as a rely-on-it product: not yet** — three specific things gate that.

### 14a. Where it stands (after five review rounds, v2.1.3)
Genuinely crossed from "impressive pitch" to "working, honest, security-serious tool": every legitimate
defect fixed with executable proof, overclaims retracted in plain language, CI added, a real multi-plan demo,
an MCP server, and a persona subsystem shipped; the maintainer even caught a CRITICAL in its own security
guard by reviewing its own output. Full test sweep green (6 phases), validator + nonce sandbox survived every
adversarial probe, reproducibility works as claimed, docs unusually candid. **Two load-bearing gaps remain:**
(1) the headline empirical claim — a cheap ~12B local model carrying the implementer role on non-toy work —
is **unproven in anything shipped** (all green results here used a strong stand-in model); (2) it's a
single-maintainer project with no community, no proven install base, and no benchmark behind the cost story.

### 14b. ✅ Publish now — as an honest open-source project and idea
It's MIT, it works, it's already public, the docs are candid, and its combination is genuinely unoccupied.
Announcing it (HN, the spec-driven-dev community, a post) is reasonable **today**, *if the framing matches the
evidence*:
- Lead with what's **proven**: deterministic/reproducible builds, a real acceptance gate, provenance by
  construction, strong sandboxing — and the method itself.
- Frame the local-model economics as a **design and an invitation to test**, not a demonstrated result:
  "here's the method and a demo; run it on your rig and tell us."
- Keep the existing honest caveats (private flagship not in repo; benchmark pending; single maintainer).

### 14c. ⚠️ Not yet — for broad "it just works for everyone" promotion
A non-expert expecting a polished Cursor/Copilot experience will hit real friction: Python-only,
greenfield-first (no "adopt my existing code" path), the spec-writing discipline is genuine work, and the
"cheap local model" outcome depends on the user's own GPU/model, which is undemonstrated. Mass-marketing it
as reliable out-of-the-box would over-promise.

### 14d. The three things that flip it to unqualified "publish broadly"
1. **Run the promised benchmark on real local hardware** — hard tasks where one-shots fail, the rebuild axis,
   metered cost. Highest-leverage missing evidence; it's the line between "interesting method" and "proven
   tool." (This is also §10 Rec #5, still open.)
2. **A 5-minute onboarding a stranger can't fail** — finish `lathe init` + a PyPI quickstart that detects a
   local model and builds a demo green (today success still depends on wiring endpoints correctly).
3. **Reduce bus-factor risk** — a CONTRIBUTING guide, a couple of external contributors, or a clear
   "reference implementation / solo project" label so adopters know what they depend on.

### 14d-followup. Maintainer response (PR #1) — reported, NOT independently verified
The maintainer replied agreeing with the §14 verdict and reported a **first benchmark on real hardware** —
the item §14d called highest-leverage: the implementer role on a cheap local model (reported as
`ornith-1.0-9b-Q4`, 9B/4-bit via llama.cpp), analyst out of the loop, through the real gate — **7/8 (88%)
pass within 5 tries, 6/8 (75%) first-pass; the one failure (an arithmetic-expression parser) was correctly
refused by the gate rather than shipped wrong; pinned rebuild = 0 model calls.** If accurate, this is the
**first non-model-contingent datapoint** for the core "cheap local model carries the implementer role"
thesis — genuinely meaningful progress.

**Reviewer's stance (unchanged until verified):** this is **maintainer-reported and NOT independently
verified by this review** — I have no access to that model or hardware, and the model name is one I cannot
corroborate. Consistent with this review's standing discipline (a claim counts when its artifacts support
it — the same test that caught the B4 "export-gap" story), the core claim stays **"unproven in what I could
independently test"** until the benchmark harness, task set, and raw run log are committed and reproducible
(ideally wired into CI per §14d). The result is a promising first signal, not yet verified evidence; the ask
is simply: make it reproducible and it converts from "reported" to "verified."
**Publish it — as an honest open-source project and a well-argued idea, with framing that promises the method
and invites testing, not a proven product.** It is trustworthy enough to stand public scrutiny (that is
exactly why it improved so fast and credibly across five rounds). Just don't let the announcement claim the
one thing the repo doesn't yet prove — that a cheap local model makes it all work. Land the benchmark and the
frictionless quickstart and it moves from "worth trying" to "worth adopting."

*Caveat consistent with this review's byline: this is the reviewer's judgment, and the reviewer is the same
model that performed the audit — a second, independent party (human or a different model) should pressure-test
this publish call, especially 14d item 1, before it drives a launch decision.*

---

## 15. Open defects — consolidated fix list for the maintainer

> **UPDATE — v2.1.4 (`0aac423`): this list is CLOSED, and I independently verified the fixes I could run.**
> D7 (`test_d7_autospawn.py` — ALL PASS: real persona fetch + `@<md>` lens injection), D5a/D5b
> (`test_analyst_guard_e2e.py` — ALL PASS: wrong-200 rejected, no-backend fails loud), D8 (my exact failing
> phrasings "authentication bug"/"login credentials" now match), and the **test-ack gate** (`LATHE_TEST_ACK`,
> `lathe ack`, `tools/test_ack.py` — real; closes the "gate the analyst's tests" mechanism from
> `METHODOLOGY_ENFORCEMENT_VALIDATION.md`) all verified by me on the rebased branch. **Not independently
> verifiable here** (need a local model): transitive pin invalidation (`test_pin_deps_e2e.py`) and the
> `ornith-1.0-9b-Q4` hard-set benchmark — recorded as maintainer-reported. The list below is the historical
> record.
>
> **UPDATE — v2.1.5 (`0c62570`): methodology mechanism #2 (requirement→test traceability) landed, and I
> independently reproduced it.** `review_tests/test_traceability.py` runs **12/12** against the v2.1.5
> validator in a fresh worktree — the enforcement half (unmapped criterion / dangling ref / out-of-range
> index / duplicate id all REFUSED; criteria-free plans still valid) is endpoint-independent, and I drove
> step 4's real gated build with a local implementer stub to confirm `lathe trace` emits the actual
> criterion→test→**pin→model** matrix (real pin hash `8c09…`, model column, coverage summary). This is the
> first of the six comprehensiveness mechanisms in `METHODOLOGY_ENFORCEMENT_VALIDATION.md` to reach
> done+accepted (scorecard now 1/6 done, 1/6 partial). The maintainer also reports having reproduced the two
> items I was sandbox-blocked on (transitive-pin invalidation; ornith-9b at 7/8 this run — honest
> regeneration variance vs the deterministic 8/8 pinned replay) — those remain *maintainer-verified, not
> reviewer-run* here.
>
> **UPDATE — v2.1.6 (`f7047d1`): methodology mechanism #1 (regression-test-must-fail-on-old-code) landed,
> and I independently reproduced it.** `review_tests/test_regression_proof.py` runs **8/8** on a real gated
> build (I drove it with a prompt-aware local implementer stub), and the pure gate logic
> (`tools/regression_proof.py`) checks **6/6** directly. The core assertion holds: with
> `LATHE_REGRESSION_PROOF=1`, a *changed* function whose new tests all pass on the old accepted impl is
> **REFUSED before any generation** (`tok_total == 0`), while a change carrying a test that genuinely fails
> on the old code proceeds green; new functions and the flag-off path are exempt. That's **2 of 6**
> comprehensiveness mechanisms at done+accepted (scorecard now 2/6 done, 1/6 partial). The word
> "comprehensiveness" now hinges on the last hard one, **#3 mutation-score threshold**.
>
> **UPDATE — v2.1.7 (`b1682ed`): STRICT / SDLC umbrella (`LATHE_STRICT=1`) — composition layer, not a new
> mechanism; independently reproduced.** `review_tests/test_strict_mode.py` **7/7** on a real gated build +
> **8/8** on the pure policy logic (`tools/strict_mode.py`). Under the flag, all development is forced
> through CRITERIA (#2) + test-ack (#4) + regression-proof (#1) + mutation-probe block — and #1 is
> **generalized from bug-fix-only to every changed function** (verified: a no-proof *enhancement* is
> REFUSED). Explicit env vars still override the umbrella; default off = no behavior change. Scorecard count
> unchanged (2/6 done, 1/6 partial) — strict mode composes what's built, and #3 is still absent from it, so
> the "comprehensiveness" line stays locked. Details in `docs/METHODOLOGY_ENFORCEMENT_VALIDATION.md`.

Everything below is currently **not working as one would expect it to**, verified against the shipped tree.
Grouped here so it can be fixed in one pass. D7–D8 are new from the persona/capability investigation
(round-6); D5–D6 were surfaced earlier and remain open.

| ID | Sev | What's wrong (verified) | Fix |
|---|---|---|---|
| **D7** | **High (confirmed bug)** — maintainer confirmed the auto-fetch-on-decision behavior is intended, so this is a genuine defect (a fix is already in progress) | **The persona decider never auto-fetches a missing expert.** The fetch-and-create *mechanism* works (`review_tests/test_persona_fetch.py`, 6/6, GitHub call mocked because api.github.com is 403 here). But no decider triggers it: `review auto` (`lathe.py` ~line 250) selects from a **hardcoded 7-capability list mapped to vendored lenses only**; the planner (`planner_prompt.py:_expert_lenses`) injects a non-vendored expert's **name+capability as a text hint** but never fetches/instantiates the body; the only real pull-and-create is the **user-invoked `lathe agent --spawn`**. So "a decider that needs an absent expert taps the library, pulls the code, and creates the persona" is **mechanism-present but not auto-wired**. | When a decider selects a catalog capability with no vendored persona, call the license-gated `_spawn_one` and inject the fetched persona **body** (not just its name) — reusing the existing permissive-license gate and fail-closed behavior. Wire it for both `review auto` and the planner. |
| **D8** | Medium | **Persona/decider matching is exact-token word-overlap** (`agent_router.score_match`/`pick_best`/`select_agents_for_goal`) — no stemming/synonyms/embeddings. Verified: `"auth vulnerability"` matches the security persona, but `"authentication bug"` → **no match**, `"login credentials"` → **no match**. So the "right expert, automatically" claim silently misfires on reasonable phrasings and won't scale past a tiny catalog. | Add lightweight stemming + a synonym map (cheap, deterministic, keeps the LLM-independence), or an optional embedding match; at minimum expand each catalog entry's capability string with common synonyms. |
| **D5b** | Medium | **A well-formed-but-wrong 200 from the analyst endpoint is undetectable.** `review`'s D3 fallback triggers only on connection error / non-2xx / empty completion, so a stale-but-reachable proxy returning a syntactically valid but semantically wrong 200 is **accepted → silent junk verdict**. | Content/schema-validate the analyst response (or add a second-opinion check); at minimum document that a wrong-200 is undetectable and don't claim the fallback covers it. |
| **D5a** | Low | **Both-backends-dead path is unspecified.** `HARNESS_CLAUDE_URL` set but returning non-2xx/empty, **and** no `claude` CLI present (the air-gapped niche) → URL rejected → fallback to CLI → CLI absent. Terminal behavior isn't defined/tested. | Fail loud: "no usable analyst backend", rc≠0; add the case to the test matrix. |
| **D6** | Low | **`should_auto_commit` silently disables on an unrecognized non-empty value** (`LATHE_AUTO_COMMIT=enabled`, `=2`, …). Direction is safe (fails closed), but a user who thinks they enabled commits gets no signal. **Maintainer reports FIXED (commit `5f19c93`) — not yet independently verified by this review (my branch is behind that `main` commit); re-verify on next rebase.** | Warn-log on any non-empty value outside `{1,true,yes,on}`: "unrecognized LATHE_AUTO_COMMIT value '<x>' — treating as disabled". |

None of these block the green sweep (they're edge/wiring/quality issues, not core-path breakage), but each is a case where the *stated or expected* behavior and the *actual* behavior diverge — the class of gap this review exists to surface. Fix order suggestion: **D7** (it's the "personification" feature the project is actively promoting — maintainer has confirmed it's intended and a fix is underway), then **D8** (same subsystem), then **D5b/D5a/D6**.

**Verification hook:** `review_tests/test_persona_fetch.py` currently proves the fetch mechanism with the
decider→spawn chain wired by hand. Once D7 lands, that test should be extended to drive `lathe review auto`
(and the planner) over code whose domain has no vendored persona and assert the harness *actually* pulls and
injects the non-vendored persona body — turning D7 into a standing regression test.

---

## Appendix — reproducing this review

```bash
python review_tests/run_all.py         # full sweep: 6 phases, manages its own mock endpoints
python review_tests/battery_security.py   # just the adversarial security battery
LATHE_REVIEW_USE_CLI=0 python lathe.py review correctness lathe.py   # B3 URL path
```

Environment: ephemeral Linux container, Python 3.11.15, no GPU/docker; both model endpoints served by the
reviewing agent (prompts logged to `review_tests/_prompts_*.log` during runs). The B4 repro intentionally
creates commits; the sweep leaves them for inspection — `git reset --hard` afterwards, as documented in §3.
Market claims in §8 are from five web-research sweeps with primary-source citations, compiled 2026-07-02;
GitHub star counts were verified live via the GitHub API the same day.

**This review was itself put through the harness under review** — precisely: `lathe review adversarial
LATHE_REVIEW_V2.md` runs a second, independent frontier-model pass (Opus via the `claude` CLI, the
harness's preferred path). Per this review's own D4, that is a **claim-review, not a gate** — an LLM
reading a document, with no mechanical claim-verification power — so it earns no more authority than any
independent expert read. What it demonstrates is the harness's review *plumbing* and the value of an
adversarial second pass, and its findings stand on their own merits. The first pass returned five
findings, all legitimate: a "verified end-to-end" claim about the repair
loop that the v2 method could not support (the stand-in implementer never fails — the same
artifact-without-reachable-path failure mode this review indicts in §3), an unverified assumption in
Rec #1 (`should_auto_commit(None)` — in fact covered by the spec's tests, now stated explicitly), a
priority-ordering hazard in Recs #2/#3, an off-by-one in the §1 case count (33→34), and an over-strong
Rec #4 that would have removed a useful fallback. All five were folded back into this document before
publication, per the harness's own review doctrine.

A **second adversarial pass** was run after §11 was added. It returned six findings; five were legitimate
and are folded in above (a genuine §10↔§11 ordering self-contradiction, the authority-borrowing wording
this paragraph now corrects, the model-contingency split in §4, a broader fallback trigger in Rec #4, and
inline dating of market figures). The sixth — its HIGH — claimed the prescribed B4 fix was unverified for
string inputs like `"0"`; its *concrete failure scenario is refuted by evidence* (the spec's own tests and
this review's `unit_functions.py` both assert `"0"`/`"no"`/`""` → False), but its meta-point stood: the
document hadn't *stated* that evidence, and now does (Rec #1). That asymmetry — reviewer wrong on the
facts, right about the missing verification statement — is itself a fair sample of what LLM review passes
do and don't give you: they catch unstated assumptions reliably, and their own claims also need checking.
A **third adversarial pass** was run after the §12 round-3 addendum was added — and it produced the most
valuable findings of any pass. It raised a **CRITICAL** (the whole "independent/verified" vocabulary rests
on a model validating its own outputs — now disclosed in the byline and TL;DR), a **HIGH** (I'd credulously
accepted B4's "export-gap" root-cause story, exempting it from §3's own standard — I then checked git,
found the story is *contradicted* by the shipped tree, and corrected §12a), a second **HIGH** (the 46/46
banner needed its model-contingency caveat attached — done), and three MEDIUM/LOW items (the B3+D3 both-dead
path → D5; harness.db staging now confirmed covered by their test + gitignore; the truthy-set near-misses →
D6). All were folded in. Note the pattern across three passes: the harness's LLM reviewer reliably catches
**unstated assumptions, internal contradictions, and self-flattering narratives the author is blind to** —
and on the B4 root cause it pushed me to a git check that overturned a claim I'd have otherwise printed. It
is not an independent oracle (it's Claude reading Claude), but as an adversarial forcing-function it earned
its place three times over. A **fourth adversarial pass** was run after §13 (round-4) was added — its findings, all folded in: two HIGH
(the security battery's coverage is bounded by my own threat model — adversary = oracle, now stated; and the
"46/46 GREEN" banner needed its model-contingency caveat attached at the banner, not just in §4 — done), a
MEDIUM that caught my B4 "PROVEN (unset **and** =0)" claim overstating what my *independent* repro had run
(I only had unset independently — so I **ran the =0 and =1 states independently** too, recorded the hashes,
and the claim is now true), a MEDIUM that the advertised one-command mutates git (warning moved to §1), and
two LOW (the §8 market figures are uncorroborated web-research — now disclosed; and a warn-log suggestion
for `LATHE_AUTO_COMMIT`, which is the author's to add). The pattern across four passes is consistent and
worth stating plainly: **the harness's adversarial reviewer reliably catches the reviewer's own
label-drift, overclaims, and unstated assumptions** — here it forced a real extra repro and three honesty
qualifications. It remains Claude-reading-Claude (not independent), but as a forcing-function against my own
blind spots it has earned its keep every round.

**Round-5 — the persona-driven, multi-lens critique (the most comprehensive pass), with log verification.**
On request, I ran the report through `lathe review auto LATHE_REVIEW_V2.md` — which fires the harness's
**decider** to select the applicable expert personas rather than a single fixed lens. The decider chose
**four**: correctness, adversarial, security, maintainability, each backed by its vendored CE persona
injected into a **real Opus** call (not the mock). **I verified from the harness's own log that this
genuinely happened before trusting it:** the run wrote four distinct archives under
`projects/agentic-harness/docs/ce/review_{correctness,adversarial,security,maintainability}.txt` with
staggered fresh mtimes (04:50:27 → 04:53:25, one per sequential Opus call), each containing substantive,
document-specific output — the maintainability persona correctly recognized the file is prose not code and
declined; the security persona found nothing material; correctness and adversarial each returned real
defects. That per-persona distinctness + timestamp spread is the evidence it was four genuine model calls,
not a stub. Findings folded in:
- **Both correctness and adversarial independently caught the sharpest one:** "**full sweep GREEN 46/46**"
  was label-drift — 46/46 is the CLI-matrix *phase* count, not the 6-phase sweep total; presenting it as
  the whole-sweep denominator is the exact green-label-drift this review indicts in Lathe. Fixed everywhere
  (§12b now lists per-phase totals).
- **My D3/D5 was internally incoherent and over-claimed:** a well-formed-but-wrong 200 is undetectable by
  the fix's connection/non-2xx/empty triggers, so my "D3 matches Rec #4" claim was false and D5 conflated
  two different paths. Split into D5a (fail-loud gap) and D5b (the unresolved semantically-wrong-200 case).
- **The B4 `=1` branch is model-contingent, not model-independent** (it needs the implementer to reach
  `commit()`); and the `60a421a→dadc2e2` hash pair is my one run, not two independent confirmations (the
  author's test is a separate scratch run with different hashes). Both corrected in §12a's row.

That the *persona* pass surfaced strictly sharper, more specific defects than the four prior single-lens
passes is itself a data point about the feature under review: the decider-selected multi-persona critique
is materially more thorough. The full findings of all five passes are archived by the harness at
`projects/agentic-harness/docs/ce/review_*.txt`. Verdict from `lathe flow doc-review --run`: recorded in
the commit history alongside this file.
