# Capstone Review — Lathe v2.16.0

> **✅ ALL FINDINGS RESOLVED in v2.17.0–v2.18.0 (independently re-verified).** The maintainer fixed the full
> set (issues #17–#21). Re-probed against v2.18.0: **#17** — `review auto` / `review <lens>` / `trace <stem>`
> all run cleanly (the CLI-regression class is closed); **#18 H2** — `grade_update`/`finding_score` are now
> called (`persona_orchestrator.py:177-203`), grades no longer dead; **#18 H3** — the orchestrator is wired
> into the review path (`lathe.py:317`); **#19 M1** — `set_selection` now called (`lathe.py:311`); M2 / #20 /
> #21 per the changelog. The findings below are retained as the v2.16.0 point-in-time record, not open defects.

*Independent capstone review of the state after the operating-contract + persona-redesign work landed.
Same method as prior rounds: **WITHOUT-harness executable probes** (re-ran every prior stress test + the qa
gates), **WITHOUT-harness analytical** (four parallel adversarial review streams, each self-verified; all
HIGH findings independently re-verified against `file:line`), **WITH-harness** (`lathe review`), and a
**docs-vs-code** audit. Every finding is grounded in the shipped code at `v2.16.0`.*

## What held under probing (foundations are solid)

- **No regressions.** Every prior gate fail-open is still closed; `spine_gate` 5/5, `manifest_contract_gate`
  6/6, `run_gates` 10/10 green.
- **Manifest `finally`-emit is genuinely un-skippable** (return / raise / `SystemExit` / SIGINT all pass
  through), writes are atomic (`_atomic_write`), the integrity self-hash really covers the object.
- **Spine re-entrancy guard is sound** (guard-forge defeated; process entry force-clears it); `LATHE_SPINE=off`
  is recorded, not silent.
- **UCB1 selection math is correct** (unseen → explore, grade → exploit); `adv_verdict`, `pbt_sample` (seeded,
  deterministic), `mutation_equiv` (now 24 seeded PBT samples, not the old fixed oracle), and `regime` all
  **fail closed** — the safe direction.

## Theme

The operating-contract **promotion** (Phase 2a/2b) shipped with `argmap` **designed but never wired**, and
several manifest/persona setters that are **never called**. The machinery passes its unit tests but isn't
fully connected to the live flow: **strong architecture, incomplete integration** — the recurring pattern,
now in the newest code.

## Findings (cross-verified, ranked)

### HIGH

**H1 — Dead `argmap` → a class of CLI regressions (root cause).**
`argmap` in `CONTRACT_FOR` (`workflows.py:198-205`) is never read; `_run_workflow` (`lathe.py:1813-1814`)
replaces `{args}`/`{files}`/`{plan}`/`{goal}` all with the same `tgt = " ".join(rest)`. Confirmed breaks:
- `lathe review auto <files>` → `review auto auto <file>` → `targets do not exist: …/auto` → **BLOCKED** *(live)*.
- `lathe review <lens> <files>` (e.g. `review security foo.py`) → lens mis-binds as a filename → **BLOCKED**;
  plain `lathe review foo.py` silently forces decider mode instead of the documented `correctness+adversarial`.
- `lathe build <stem>` / `build <plan> <model> <tries>` → the build step succeeds but the `trace {plan}` step
  (`workflows.py:152`) re-dispatches to `cmd_trace`, which resolves via `os.path.abspath` (`lathe.py:1568`),
  **not** `_resolve_plan` — so `trace <stem>` → `no such plan` → **BLOCKED** → nonzero exit on a successful
  build (`--json` dodges promotion, so CI is unaffected; interactive build is not).
**Fix:** implement argmap-aware binding (bind argv[0]-as-plan / lens-aware review), or make the review step
`review {args}` (passthrough) and `cmd_trace` use `_resolve_plan`.

**H2 — Persona work-based grades are dead code.**
`grade_update` / `finding_score` (`persona_grade.py`) have no live callers; `record_run` is invoked once with
`contributions={}` hard-coded (`persona_spawn.py:124`); nothing writes `grades.json`. So `load_grades()`
always returns `{}` and every persona's exploit term is `grade=0` → **UCB1 degrades to explore-by-visit-count;
a graded persona is never exploited.** The "work-based grades" half of the redesign never engages.

**H3 — The live review-lens decider still uses the old word-match.**
`lathe.py:282` (`select_agents_for_goal`) and `planner_prompt.py:77` still select via word-overlap and do not
record to the usage ledger. UCB1 only governs the *additive* `auto_spawn_for_goal` fetch. The headline "word-
match retired, usage recorded" is only half true in the live flow.

### MEDIUM

**M1 — Manifest audit fields are never populated.** `set_selection`, `set_goal`, `add_model` (`manifest.py`)
have zero callers, so every manifest ships `selection={personas:[],lenses:[]}` (the whole #9 "who
contributed" payload), `intake.goal=null`, and `models=[]` — even for `do`/`review`/`sdlc`, which do select
and do have a goal. (Usage/contributor/gate fields *are* populated via the engine hooks.)

**M2 — Degraded `finalize` can clobber a valid record with a self-inconsistent hash.** If the JSON write
succeeds but the `.md` write raises, the `except` re-writes the JSON as `partial:true` **without recomputing
`manifest_sha256`** (`manifest.py:212-219`) — the one integrity invariant the file provides is broken on that
path.

**M3 — CONTRACT_FOR flags `front_end`/`select`/`writes` are decorative.** Only `workflow` and `gate` are read
by `run_spine`. `do` advertises `front_end:1, select:1` but `build-from-goal` has no clarify/assume/persona
step — so "every write composes front-end + gates + adversarial" is not enforced by these flags.

**M4 — Adversarial-synth can be dodged.** It is off by default (`LATHE_ADV_SYNTH`), and even armed,
`needs_adversarial` only fires when the plan declares `kinds:['gate']` or is named `gate/valid/strict/guard`
— a weak gate plan named otherwise is never probed and pins. `admit_cases` also admits vacuous `assert True`
(`adv_synth.py:36`) with no discrimination check. (`adv_verdict` itself is fail-closed; the selection in
front of it is fail-open.) Generation is delegated to an analyst LLM call (`engine_v2.py:502`), not
self-contained.

**M5 — Docs drift.** `review auto` is documented as the primary form in `README:89`, `CLI_REFERENCE:70`,
`LATHE_COMMANDS:130`, `PERSONAS.md:40/92` — all now BLOCKED. `README:169` says "current: v2.2.4" (actual
2.16.0). "Six standing gates" (`README:138`) → actually 10. `CLI_REFERENCE` "every env var / 53" → `REGISTRY`
has 66 (missing the spine group `LATHE_THINK`/`LATHE_SPINE`/`LATHE_RUN_ID`, `LATHE_PERSONA_UCB`, the adv-synth
group). The reviewer's own persona docs said "default OFF" (v2.16.0 flipped to ON *after* PR #14) — **fixed in
this PR**.

### LOW
- `lathe`/`help`/`-h` emit no manifest (return before `_manifest_begin`) — no work done, minor.
- `clarify` declares `writes:1` with no gate (writes a doc brief, not code).
- `mutation_equiv` `exec`s candidates with full `__builtins__`, unsandboxed (inputs are already-vetted).

## With-harness vs without-harness

- **With-harness** (`lathe review`) surfaced H1 *by failing on it*, and produces real findings on a bare file —
  but is slow (timed out on a full module) and its own selection is the old word-match (H3), so it is blind to
  the wiring gaps.
- **Without-harness** (subagents + executable probes) found the dead code (H2), dead argmap (H1), empty
  manifest fields (M1), and the build regression that the harness cannot introspect about itself.
- They **agree** the foundations are sound; the without-harness pass found strictly more.

## Bottom line

Every prior fix holds and the architecture is sound, but the contract promotion introduced a **class of CLI
regressions** (dead `argmap`) and shipped **half-wired features** (dead persona grades, empty manifest
selection, decorative contract flags). **3 High, 5 Medium, 3 Low — all grounded to `file:line`.** These are
integration gaps, not foundational flaws: the pieces exist and pass their unit tests; they need to be wired
into the live flow.

*Reproduce: the executable probes are in `scratchpad/*_stress*.py`; H1 reproduces with `python lathe.py review
auto <file>` (BLOCKED) vs `python lathe.py review <file>` (works).*
