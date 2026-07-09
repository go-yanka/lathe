# Changelog

All notable changes to Lathe. Dates are absolute. This project ships **no model weights**.

## v2.47.0 — 2026-07-08 — loop #2 TARGETED REPAIR: fix the exact failure, not a blind re-roll (convergence complete)

The second half of convergence. Best-of-N regenerated the whole artifact from the SAME prompt every attempt, so
a model that ignored the spec or crashed on an edge case just failed N different ways (the helicopter's attempts
2 & 3: undefined-variable crash; ignored the physics numbers). Now a retry is handed its OWN failed file + the
EXACT gate failure and told to fix precisely that.

- `tools/repair_prompt.py` — `build(task, failed_code, failure_reason)` composes a self-contained repair prompt:
  the spec, the exact failure ("held Space -> craft went DOWN dy=143.8; honor the spec's numbers EXACTLY"), the
  previous file, and a fix-ONLY / do-not-rewrite directive + raw-file output contract. Truncates to stay in
  context; never raises. `reason_from()` turns the engine's structural/functional result into that reason string.
- `engine_v2.py` — the whole-file artifact loop now remembers each failed candidate + its exact reason and, on
  the next attempt, builds a targeted-repair prompt instead of re-rolling the same spec blind. Default on;
  LATHE_TARGETED_REPAIR=0 restores blind best-of-N. Skeleton-fill artifacts keep their existing tiny-region path.
- `qa/repair_prompt_gate.py` (regression now 25 checks) — proves the repair prompt carries the exact failure +
  failed code + fix-only directive + output contract, that reason_from picks structural vs functional, that a
  huge file is truncated, and that it never raises.

With v2.46.0 (spec self-review before the implementer) this closes BOTH loops: the input is made consistent
BEFORE the build (loop #1) and the implementer's specific mistakes are corrected DURING it (loop #2). Detection
(25 gates) now has a matching convergence engine.

## v2.46.0 — 2026-07-08 — THE CLOSED LOOP: the spec refines ITSELF to consistent BEFORE the implementer runs

The persistent gap named this session: gates DETECT bad output but nothing iterates the SPEC toward correct, so
a contradictory test wastes the implementer on an unwinnable target (the helicopter: a WORKING copter rejected
by its own "score in 1.2s vs 5s grace" test). This closes it — draft -> detect contradiction -> analyst REFINES
spec+test -> consistent -> only THEN engage the implementer.

- `tools/spec_review.py` — `converge(spec, behavior, analyst_fn, max_rounds)`: loops critique->refine until the
  DETERMINISTIC bar (spec_test_consistency) is clean, so it always terminates and "clean" is objective; the
  analyst's LLM self-critique feeds the refinement but never decides termination. Analyst injected; never raises.
  PROVEN LIVE: the real analyst took the helicopter contradiction and, in ONE 28s call, widened the score-check
  window 1200ms -> 5500ms (past the 5s grace) — clean, no remaining contradiction.
- `engine_v2.py` — the behavioral branch now REFINES before building: on a spec<->test contradiction it runs the
  loop and rebuilds the gate + the implementer prompt from the reconciled spec. CHEAP: 0 analyst calls when the
  spec is already consistent, 1 only when a contradiction must be fixed. LATHE_SPEC_REVIEW=0 warn-only, =deep
  adds the LLM critique; LATHE_SPEC_TEST_STRICT still refuses if unresolved.
- `qa/spec_review_gate.py` (regression now 24 checks) — proves convergence with a stub analyst: a contradiction
  refines to clean within max_rounds, a clean spec is untouched (round 0), an unfixable one ends clean=False
  (surfaced, not hidden), never raises.
- `env_catalog.py` — LATHE_SPEC_REVIEW / _MODEL / _TIMEOUT documented.

This is the shift from DETECTION to CONVERGENCE: the 23 gates define "correct"; this loop pursues it. Had it
been live, the helicopter's attempt-1 (a working copter) would have shipped.

## v2.45.0 — 2026-07-08 — spec<->test consistency: catch a build spec that contradicts its own acceptance test

Prompted by a real failure: a helicopter build produced a WORKING copter that its own test rejected. The spec
said "no obstacles for the FIRST 5 SECONDS" while the acceptance test said "hold Space 1.2s -> #score must
INCREASE". Score is obstacle/distance based, so in 1.2s it is legitimately 0 — a correct build fails an
impossible test. The implementer can't win; re-rolling the artifact never fixes the TEST. New failure class.

- `tools/spec_test_consistency.py` — pure `check(spec_text, behavior)` flags where the behavioral test
  contradicts the spec: score-vs-grace (score-increase window inside a stated no-score/grace period),
  undeclared-selector (test asserts on an element the spec never says to create), motion-vs-paused (an idle
  trial expects motion while the spec says the game starts paused). Deterministic, never raises.
- `engine_v2.py` — before compiling a behavioral gate, the engine runs the check: a contradiction prints a loud
  `[spec<->test WARNING]` (advisory) and, under LATHE_SPEC_TEST_STRICT, REFUSES the build so the analyst fixes
  the TEST rather than wasting attempts. Proven: run against the actual failed build, it flags BOTH real
  contradictions (score-vs-grace + motion-vs-paused).
- `qa/spec_test_consistency_gate.py` (regression now 23 checks) — reproduces the helicopter case and proves the
  check catches it, flags an undeclared selector, stays quiet on a consistent spec, and does not false-flag a
  long-enough window.
- `tools/failure_modes.py` — new guarded class `spec-test-inconsistent` -> `spec_test_consistency`.
- `env_catalog.py` — LATHE_SPEC_TEST_STRICT documented.

## v2.44.0 — 2026-07-08 — MASTER_PLAN F4: code/docs/scripts/config layout for multi-file projects (plan COMPLETE)

The final code item. Every A/B/C/D/E/F item on the MASTER_PLAN is now done and gated.

- `tools/project_layout.py` — classify(file) buckets into code/docs/scripts/config; is_multifile_project()
  triggers ONLY on 2+ code files (a lone artifact + its docs is not a project — single-goal workspaces stay
  flat); organize() writes a PROJECT.md layout map and, opt-in, relocates files into bucket subdirs.
- `lathe.py` — after a `do` build, a genuine multi-file project gets a PROJECT.md map; physical reorganization
  is opt-in via LATHE_PROJECT_LAYOUT=1 (so a built file is never silently moved and a relative reference broken).
- `qa/project_layout_gate.py` (regression now 22 checks) — proves bucketing, the multi-code-only trigger,
  plan-without-move + PROJECT.md, and apply=True relocation.
- `env_catalog.py` — LATHE_PROJECT_LAYOUT documented.

Plan status: A,B,C,D,E,F complete + gated. Remaining (G) is OWNER-GATED — needs credentials/data/hardware.

## v2.43.0 — 2026-07-08 — MASTER_PLAN F1/F2/F3: workspace intent docs + honest naming + clearer help

- `tools/workspace_docs.py` (F1) — every `lathe do` workspace now gets a GOAL.md (the intent + the resolved
  assumptions the build was made to + the interview panel) and a README.md (what each file/dir is). The folder
  says what it is at a glance; machine state stays in dotfiles. Best-effort — never blocks a build.
- `lathe.py` help (F2/F3) — the header now names the two PLUGGABLE roles, THINKER (analyst) + BUILDER
  (implementer), and states the analyst need NOT be Claude (any OpenAI-compatible endpoint). `lathe do` is
  documented as THE canonical one-shot; bare `lathe "<goal>"` as its labeled shorthand.
- `qa/workspace_docs_gate.py` (regression now 21 checks) — proves GOAL.md carries the goal + every assumption +
  the panel, README names the workspace + files, empty-assumptions is handled, and a bogus dir never raises.
- F4 (project-level code/docs/scripts/config layout for multi-file PROJECTS) remains OPEN as optional polish —
  it applies only to multi-file project mode; the common single-goal path now has GOAL.md/README.

## v2.42.0 — 2026-07-08 — MASTER_PLAN E4: persona ratings LEARN from review outcomes (E block complete)

Ratings used to come only from a dedicated `lathe agent rate` run. Now a real review nudges the lens's rating
automatically — the decider learns which lenses reliably deliver, closing the persona feedback loop.

- `tools/outcome_feedback.py` — `record_review_outcomes(lens_verdicts, load_ratings, save_rating)` blends a
  per-lens outcome score into its prior rating via the existing persona_grade math (persistence INJECTED, so
  pure + testable, store format unchanged). Honest about the coarse signal: EWMA-blended with a heavy prior so
  one review nudges and a consistent pattern moves it; a lens that engaged (valid review) scores up, an
  inoperative/non-review (D5b) gives NO signal (skipped).
- `lathe.py` — `cmd_review` captures each lens's exit verdict (engaged vs inoperative) and, opt-in via
  `LATHE_GRADE_FEEDBACK=1`, feeds them to the ratings store after the review.
- `qa/outcome_feedback_gate.py` (regression now 20 checks) — proves: engaged EWMA-nudges up (blended, not
  overwritten), inoperative + fetched-@-path lenses are skipped, a new lens starts from prior 0.5, a broken
  saver never propagates. The learning loop can't corrupt the store or silently regress.
- `env_catalog.py` — LATHE_GRADE_FEEDBACK documented.

## v2.41.0 — 2026-07-08 — MASTER_PLAN E1/E3: prompt-architect in the panel + an HONEST (real) semantic decider

- `tools/semantic_decider.py` (E3) — the base decider (agent_router) is synonym-expanded WORD-OVERLAP; calling
  it "semantic" overclaimed. This adds the real thing: `decide(goal, candidates, k, mode)` where mode=semantic
  asks the analyst to RANK candidates BY MEANING (PROVEN LIVE: for "users get logged out and can't prove who
  they are", lexical found only 1 match, semantic returned the full k with sound reasoning). Crucially it
  returns (names, HOW) — 'lexical' | 'semantic' | 'lexical-fallback(analyst-unavailable)' — so nothing ever
  silently claims semantic when lexical ran. Default stays lexical (free, no regression); LATHE_DECIDER_MODE
  opts into semantic/auto. Reuses the SSRF-guarded analyst client; never raises.
- `tools/panel_floor.py` (E1) — `with_architect()` guarantees the prompt-architect MODERATOR lens is in the
  intake panel, FIRST (it crafts the analyst's brief from the panel's questions), de-duplicated, no mutation.
- `lathe.py` — `_intake_panel` now routes selection through `semantic_decider.decide` (honest mode) and
  guarantees the architect via `with_architect`.
- `qa/persona_wiring_gate.py` (regression now 19 checks) — proves: architect always present+first+deduped;
  decider reports the true path; a down analyst falls back with a LABELED how; hallucinated candidate names
  are filtered. E1/E3 can't silently regress or overclaim.
- `env_catalog.py` — LATHE_DECIDER_MODE / LATHE_DECIDER_MODEL / LATHE_DECIDER_TIMEOUT documented.

## v2.40.0 — 2026-07-08 — MASTER_PLAN B3/B5 (+B1/B2 closed): honest command->workflow contract

WORKFLOWS_MAP found the `front_end`/`select` flags in CONTRACT_FOR were DECORATIVE — never read by the spine
(which reads only `workflow` and `gate`), yet they implied the spine did intake/persona-selection. Removed.

- `tools/workflows.py` — deleted `front_end`/`select` from every CONTRACT_FOR entry (proven 0 read-sites). The
  front-end (intake + per-assumption confirm + spec approval) runs in cmd_do; persona selection runs in
  _intake_panel/_do_review — at the COMMAND layer, which is where they were actually wired (A1-A4). Header
  comment now states only `workflow`/`gate` are behavior-bearing; `writes`/`argmap` are documentary.
- `qa/contract_hygiene_gate.py` (regression now 18 checks) — B3: no entry may carry the retired
  front_end/select keys or any key outside {workflow, gate, writes, argmap}; B5: every promoted `workflow` must
  exist with non-empty steps (no dangling `lathe flow` target). 27 contracts clean, 14 promotions resolve.
- B1/B2 closed: `do` runs its full front-end at the command layer; the runner records every declared step
  (workflow_wiring, v2.30). `sdlc <goal>` intentionally runs the requirements phase — the full 11-step SDLC has
  mandatory human review/resolve steps and is the human-guided `lathe flow sdlc`, not a single auto-promotion.

## v2.39.0 — 2026-07-08 — MASTER_PLAN A3/A4: per-assumption confirm + spec approval before build

`lathe do --interactive` now genuinely interviews: it walks EACH surfaced assumption for accept/correct/drop
(A3), then shows the refined spec (goal + resolved assumptions) and requires approval — or folds in a revision,
or aborts — BEFORE any build starts (A4). No more single blob "confirm?" prompt; no more building on unreviewed
guesses.

- `tools/intake_confirm.py` — the DECISION logic as pure, testable functions driven by an injected responder:
  `confirm_assumptions(assumptions, responder)` (accept="" , drop='d'/'n'/'-', or replacement text -> edited)
  and `approve_spec(summary, responder)` (""/yes -> approve, no/abort -> reject, other text -> revision).
- `lathe.py` — the interactive intake supplies an input()-backed responder for both steps; a revision request
  is appended to the build goal, a reject cleanly aborts with no build.
- `qa/intake_confirm_gate.py` (regression now 17 checks) — proves the logic with SCRIPTED responders (no
  stdin): accept keeps+tags, drop removes, edit replaces without mutating inputs, approve/reject/revise map
  correctly. The interview logic can't silently regress.

## v2.38.0 — 2026-07-08 — MASTER_PLAN C1/C2: the per-build adversarial second spec + refute pass

Completes the adversarial ratchet's LIVE arm (the durable registry was C3/4/5). Owner's design: a build carries
two specs — how to DO it, and how any LLM could GET IT WRONG — and the second is audited before we trust it.

- `tools/refute_auditor.py` — C1 `hypotheses(goal)`: the analyst enumerates concrete, per-goal ways ANY LLM
  implementer is likely to get THIS goal wrong (the second spec). C2 `refute(goal, artifact, hyps)`: a pass
  that ASSUMES the build is broken and judges, per hypothesis, whether the artifact exhibits it. PROVEN LIVE:
  for a helicopter goal it produced 8 expert holes (Space-scroll not suppressed, gravity not accumulated,
  obstacle-gap not guaranteed, game-loop-survives-death, canvas attr-vs-CSS size mismatch, collision coord
  space...) and refuted a fixture accurately. Reuses the SSRF-guarded analyst client. Never raises.
- `engine_v2.py` — opt-in `LATHE_REDTEAM=1`: after an artifact is written, the engine runs the second-spec +
  refute pass and records the report in the manifest. ADVISORY — the deterministic gates decide pass/fail; the
  red-team surfaces candidate new failure classes (which graduate into the registry via C4).
- `qa/refute_lane_gate.py` (regression now 16 checks) — proves the PLUMBING with a STUB analyst: parse
  hypotheses, map present->holes / none->clean, analyst-down->inoperative (never propagates), audit() composes
  both. The wire can't silently un-wire; the live red-team is non-deterministic and validated on demand.
- `env_catalog.py` — LATHE_REDTEAM / LATHE_REDTEAM_MODEL / LATHE_REDTEAM_TIMEOUT documented.

## v2.37.0 — 2026-07-08 — MASTER_PLAN D3: the ADVISORY visual judge — the harness can now SEE the page

Deterministic gates prove a page loads/animates/responds/keeps-state (D1/D2) but cannot see that it LOOKS like
the goal — a page can pass every check and still render blank, unstyled, or off-topic. D3 shows a screenshot to
a vision model and records whether it looks right. PROVEN LIVE: passes real renders (heli_good 0.90,
score_good 0.92), fails a blank page (0.97, "completely blank/white, no canvas").

- `tools/vision_judge.py` — capture() screenshots a rendered HTML file (headless Chromium); judge() sends the
  screenshot + goal to a vision model and parses a compact JSON verdict {looks_right, confidence, issues}. The
  judge fn is INJECTABLE (stub in tests, real client in prod) and NEVER raises — a judge outage is 'inoperative'
  (advisory), not a crash.
- `tools/request_spec.py` — the SSRF-guarded analyst client gained an `images=` path: it sends OpenAI
  multimodal content (text + image_url) which the loopback proxy saves and lets Claude view. Reused, not
  reinvented — all the retry/SSRF/usage logic is shared.
- `engine_v2.py` — opt-in `LATHE_VISION_JUDGE=1`: after an HTML artifact passes its deterministic gates, the
  engine SHOWS the rendered page to the judge and records the verdict in the manifest/report. ADVISORY by
  design — it never changes the build verdict (the deterministic gates decide); it annotates. Never raises.
- `qa/vision_lane_gate.py` (regression now 15 checks) — proves the PLUMBING deterministically with a STUB
  judge (no model call): real screenshot -> good verdict maps to pass, bad to fail, a raising judge to
  inoperative (never propagates), parse_verdict handles JSON/prose/garbage. The wire can't silently un-wire;
  live model judgement is inherently non-deterministic and validated on demand (like the rig).
- `tools/failure_modes.py` — new guarded class `visual-mismatch-unchecked` -> `vision_lane`.
- `env_catalog.py` — LATHE_VISION_JUDGE / LATHE_VISION_MODEL / LATHE_VISION_TIMEOUT documented.

## v2.36.0 — 2026-07-08 — MASTER_PLAN D2: STATE assertions — a game is never certified on motion alone

Builds on D1's behavioral interpreter. Motion checks prove the controls move something; STATE checks prove the
game keeps score and is not already over.

- `tools/behavioral_gate.py` — a trial may now carry a `"state"` assertion alongside/instead of `"expect"`:
  `{"selector":"#score","op":"increases"|"changes"|"stable"}` (a DOM element must progress — e.g. score ticks
  up on a scoring input) or `{"text_absent":"game over"}` / `{"text_present":...}` (the game must NOT be over
  after correct play). Read from DOM text before/after the drive; `increases` parses the leading number. Still
  fixed-vocabulary DATA — an unknown op raises and the engine refuses the build (fail closed).
- `tools/func_gates.py` — the DEFAULT `web_canvas_game` gate gained an instant-game-over guard: EARLY (before
  it drives keys) and on VISIBLE text only, it rejects a build already showing "game over"/"you lose"/etc — the
  literal helicopter symptom ("ends as soon as it starts") — without false-failing a game a later drive
  legitimately loses. So even builds with NO analyst behavioral spec catch instant death.
- `qa/behavioral_lane_gate.py` (+ fixtures score_good/score_bad/gameover_bad) — the standing proof now covers
  3 cases: D1 motion, D2 score-state, and the default-lane instant-game-over guard. A frozen-score game and an
  instant-death game each FAIL; working ones PASS. (heli_good gained a tiny perpetual wiggle so it is never
  pixel-frozen at rest — vertical centroid, which the up/down proof uses, is unchanged.)
- `tools/autonomy_live.py` — the drafter now offers state assertions when authoring a game's behavioral spec.
- `tools/failure_modes.py` — new guarded class `state-progression-unchecked` -> `behavioral_lane`.

## v2.35.0 — 2026-07-08 — MASTER_PLAN D1: behavioral lane — proves the controls WORK, not just that pixels move

**Closes the helicopter class end-to-end.** The `web_canvas_game` gate only proved the canvas CHANGES over
time — a helicopter that falls and dies still "changes", so DEAD CONTROLS passed it. That was the tracked-open
failure class `behavioral-correctness-unchecked`. Now GATED.

- `tools/behavioral_gate.py` (TRUSTED CORE_INFRA) — a behavioral-intent INTERPRETER. The analyst authors a
  spec as pure DATA: a list of trials, each a DRIVE keyed to its argument (`{"hold":"Space","ms":900}` |
  `{"press":...}` | `{"idle":900}` | `{"click":[x,y]}`) + an `expect` in up|down|left|right|move|still.
  `build_script()` compiles it into a Playwright gate that loads the page FRESH per trial, samples the canvas
  foreground CENTROID before/after the drive, and asserts it moved as specified. The analyst picks only from a
  FIXED vocabulary — an unknown verb makes build_script RAISE and the engine refuses the build (fail closed).
- `engine_v2.py` — `functional_ref: "behavioral"` + a DATA `behavior` list is compiled by the trusted
  interpreter (a bad spec => artifact REFUSED). The plan carries NO gate code; the validator already rejects
  any injection inside `behavior` via its whole-AST danger scan (verified).
- `autonomy_live.py` — the webapp drafter now PREFERS the behavioral lane for games: it authors the
  input->response trials that encode the goal's core controls, falling back to `web_canvas_game` (liveness)
  only when it cannot state a concrete control->response.
- `qa/behavioral_lane_gate.py` + `qa/fixtures/heli_{good,bad}.html` (regression now 14 checks) — the standing
  PROOF: one spec (hold Space -> up; idle -> down) PASSES a working helicopter and FAILS a dead-control one
  that only falls. Both animate, so the old liveness gate passed both — this gate discriminates play from motion.
- `tools/failure_modes.py` — `behavioral-correctness-unchecked` flips from OPEN hole to guarded by
  `behavioral_lane`; the registry gate now tracks 3 open holes, down from 4.

## v2.34.0 — 2026-07-08 — MASTER_PLAN C3/C4/C5: the adversarial-ratchet SPINE (failure-mode registry + coverage gate)

**Owner's "keep adding them to the gates" made self-enforcing: a known failure CLASS must have a gate, or the
build says so.**

- `tools/failure_modes.py` — the curated, GROWING registry of LLM-implementation failure CLASSES we have
  actually hit, each bound to the standing gate that catches it (or gate=None = OPEN hole). Seeded with
  tonight's: wire-not-tested-e2e, silent-step-drop, contradictory-contracts, prose-instead-of-code,
  assumption-guess, gate-inoperative-blamed-spec, duplicate-capability (all guarded) + 4 tracked-open holes
  (pin-provenance-endpoint, behavioral-correctness-unchecked, false-done-unwired-tasklist, stub-satisfiable-tests).
- `qa/failure_registry_gate.py` (regression now 13 checks) — enforces the ratchet: every class claiming a gate
  MUST have that gate wired into run_gates; open holes print LOUDLY every run (never a silent gap). Proven: a
  class claiming a non-existent gate FAILS; the 7 guarded classes all verify.
- This is C3 (the checklist) + C4 (coverage enforced) + C5 (seeded). Add a failure class -> you must wire its
  gate or the registry gate calls the coverage a lie. C1/C2 (per-build refute-mode second-spec auditor) is the
  next, model-calling slice.

## v2.33.0 — 2026-07-08 — MASTER_PLAN A1: intake INTERVIEW PANEL + E2 (personas recorded for `do`)

**Intake is now a goal-matched expert PANEL, and `do` finally records which personas shaped the spec.**

- The intake upgrades from a single auditor to a PANEL: `_intake_panel` reuses the EXISTING decider
  (`agent_router.select_agents_for_goal` over agents/catalog.json + CE floor — the same one the planner
  uses; no rebuild) to pick 2-3 goal-matched lenses. Their viewpoints are injected into one merged
  assumption pass ("surface what each expert would flag, then dedupe") — panel thinks, one call asks.
- E2 DONE: the panel personas are recorded in the manifest `selection.personas` (was permanently `[]` for
  every `do` — the 'personas fire only in review' gap). Proven: a web `do` recorded
  `['correctness-reviewer','business-analyst',...]` + 11 assumptions.
- HONEST: panel QUALITY is bounded by the word-match decider (E3, still open) — a game goal can draw an
  off-topic lens. The WIRING is correct + gated (12 gates green); the semantic-decider upgrade is E3.
- Remaining in A: A3/A4 (interactive per-assumption confirm + spec approval — `--interactive` is the seed).

## v2.32.0 — 2026-07-08 — MASTER_PLAN A6: assumption gate ARMED on the web lane (bypass closed)

**The assumption gate now covers ARTIFACT/webapp plans and enforces the intake's ledger — pure wiring of the
existing gate + assumption_logic (no new gate, no rewrite).**

- Engine: the gate guard was `plan.FUNCTIONS`-only, so it SILENTLY SKIPPED every web goal (empty FUNCTIONS =
  structural bypass, per WIRING_AUDIT D2). Now fires for `plan.FUNCTIONS OR plan.ARTIFACTS`; digest over
  whichever spec list the plan carries.
- Engine: accepts a GOAL-SCOPE ledger (keyed "*", scope="goal") that `lathe do` intake writes before the
  plan name is known — trusts it for the run, skips the plan-digest freshness check. Plan-scoped
  `lathe assume <plan>` audits unchanged. Reuses `assumption_logic.unconfirmed_blockers`/`spec_digest`
  verbatim — the enforcement logic is untouched.
- cmd_do: intake writes `.assumptions.json` (the exact {ledger, confirmed} format the gate reads) next to the
  plan and ARMS `LATHE_ASSUMPTION_GATE`. assume-and-record auto-confirms → passes but is recorded +
  enforceable; unconfirmed HIGH (interactive/STRICT) → BLOCKS.
- PROVEN: a real web `do` built green with the gate armed; then un-confirming one HIGH in that plan's ledger
  and rebuilding → `engine: ASSUMPTION GATE — 1 unresolved high-materiality assumption` BLOCKED the build.
  A web plan that pre-A6 skipped the gate entirely now enforces it. 12 gates green.

## v2.31.0 — 2026-07-08 — MASTER_PLAN A (phase 1): INTAKE wired into `do` — assumptions surfaced before drafting

**The biggest bug-source fixed at the origin: `do` now surfaces the goal's UNSTATED assumptions and feeds
them into the spec, instead of letting the model silently guess (the helicopter-physics class).**

- New intake stage in `cmd_do` (assume-and-record default): before drafting, an analyst pass using the
  EXISTING assumption-auditor persona + `assumption_logic` (wire-don't-rebuild) surfaces the choices the goal
  left open — behaviour, controls, physics, edge cases, win/lose, defaults. Written to `<workspace>/
  ASSUMPTIONS.md` + the manifest `front_end` slot, and injected into the drafting prompt as RESOLVED
  ASSUMPTIONS the spec must build to.
- `front_end` manifest slot is now FILLED (was permanently `ran=False` — the 'built but not wired' tell):
  `set_front_end(ran, mode, assumptions)`. The report finally shows what was assumed.
- Flags: `--interactive` (confirm/correct the assumptions before building), `--assume` / `LATHE_INTAKE=0`
  (skip the intake).
- PROVEN on the exact goal that failed: "classic helicopter game" — old behaviour = silent guess → helicopter
  fell instantly (score 0). New = intake surfaced 14 assumptions incl. the physics (one-button hold-to-rise,
  constant gravity+thrust, instant-death), recorded + injected; the rebuilt game FLIES (played to score 12,
  full score/best/restart). The guess is replaced by a stated, recorded decision. 12 gates green.
- Next (A phase 2): the interview PANEL (multi-persona questions → moderator merge) + arming the assumption
  gate on the artifact lane so unconfirmed HIGH assumptions can block.

## v2.30.0 — 2026-07-08 — MASTER_PLAN B4: the wiring gate (declared == executed)

**The anti-disconnect gate: a workflow step that is DECLARED but not EXECUTED now fails the build.**

This is the foundational fix for the disease surfaced by WIRING_AUDIT.md / WORKFLOWS_MAP.md — capabilities
built and pinned in isolation but never wired into the command a user runs, uncaught for weeks because
nothing gated the plumbing itself.

- **Runner fix (`_run_workflow`):** every DECLARED step is now RECORDED — a placeholder that binds to
  nothing is recorded `skipped` (was silently dropped, the exact historical bug); steps after a halt are
  recorded `not-reached`. So `declared == executed` holds by construction, and any gap is visible.
- **New standing gate `workflow_wiring_gate` (regression now 12 checks):** runs the REAL runner against
  synthetic workflows (primitives stubbed, deterministic, ~ms) + checks every command-promoted workflow —
  asserts every declared step label appears in the executed record. 4/4 probes; P4 confirms all 14 promoted
  workflows satisfy declared==executed today.
- Why this is first: once it exists, wiring the front-end (intake/assumptions, MASTER_PLAN A) is
  self-proving — a declared clarify/assume step that doesn't fire fails the build. Disconnection becomes a
  red gate, not a silent rot.

## v2.29.2 — 2026-07-08

**Corrects v2.29.1 (shipped with a red gate — my error): bare-goal fix moved to the right layer.**

- v2.29.1 fixed the silent no-op by rewriting a bare goal's argv to `do` BEFORE the spine — which erased
  the manifest's routed_via="bare-goal" stamp and failed the manifest_contract T6 probe (the shared-path
  class again; I pushed without re-reading the gate — on the record). Reverted.
- Correct fix: the workflow's primitive step now matches an EFFECTIVE command ("do" for a bare goal) so the
  build step fires, while cmd stays the goal text and the manifest keeps routed_via="bare-goal"/is_bare_goal.
  The single-token typo guard stays in the entry (clear error + difflib suggestion). All 11 gates green;
  T6 restored; bare multi-word goal builds; `lathe stauts` -> suggestion.

## v2.29.1 — 2026-07-08

**Fix silent no-op: `lathe "<goal>"` (no `do`) now builds instead of just running gates.**

- A bare natural-language goal used to promote the goal-STRING-as-command through do's workflow, whose
  build step keys on the literal "do" — so it never fired, only the standing gates ran, and nothing built.
  From the user it looked like "it didn't do a thing" (found live: owner ran a goal missing `do`).
- Now normalized at entry: a bare MULTI-WORD arg is rewritten to an explicit `do "<goal>"` (builds
  correctly); a bare SINGLE token is treated as a likely command typo -> clear error with a
  difflib-suggested command, never a silently wasted build. Verified: the exact failing goal now drafts +
  builds; `lathe stauts` -> "Did you mean `lathe status`?"; real commands unaffected.

## v2.29.0 — 2026-07-08

**Workspace names say WHAT is being built and WITH WHICH model (owner design).**

- goals/<short-goal>_<model>_<MMDD-HHMMSS>/ — e.g. `conway-game-life-canvas_9b_0708-1227` instead of the
  old 60-char mid-word-truncated slug with no model info. Harness-built (`short_goal`: stopword-dropping
  keyword slug, whole-word truncation; `model_abbrev`: fable/claude/gpt names or the size token like 9b/35b).
- Class-fix in passing: `slugify_goal`'s spec was missing the explicit `import re` instruction its sibling
  got fixed for yesterday (instance-not-class — the standing gate caught the regeneration failure and the
  repaired spec is now pinned). Old-format workspaces remain valid; naming applies to new goals.

## v2.28.0 — 2026-07-08

**Post-mortem mechanisms (owner: "how do we stop this stupidness over and over"): contradictions now die at
validation or in the standing regression, not in production.**

Root causes of the v2.26 skeleton regression, named: (1) the artifact path serves TWO output contracts and
was edited reasoning about only one; (2) NO standing gate covered the skeleton lane, so the break shipped
green; (3) implementer instructions accrete across three layers (scope text, profile override, engine
envelope) with no consistency check. Mechanical fixes:

- **Contract-consistency validation:** a plan whose artifact has a skeleton (region fill) but whose prompt
  orders whole-file output ("whole file" / "<!DOCTYPE"-first reply) is now REFUSED at validation with a
  named reason — the exact contradiction that wasted 9 builds can no longer reach the engine.
- **skeleton_lane standing gate** (regression is now 11 checks): runs BOTH artifact lanes against a
  deterministic local stub implementer (~2s, zero model cost) and asserts the fill lane receives the
  REGION contract, the whole-file lane receives the FILE contract, splice+echo-strip work, and preamble
  salvage works. This gate fails in seconds on the class of change that caused the regression.
- Principle adopted: the ENGINE owns output-format contracts; plans own content specs. Any format
  instruction a drafted prompt carries is overridden by the engine envelope and cross-checked by the
  validator.

## v2.27.1 — 2026-07-08

**RETRACTION + fix: the 9B never failed Game of Life — the harness gave it contradictory contracts.**

- v2.27.0 claimed the 9B's 9 failed fill attempts showed a model limitation ("emits HTML inside the JS
  fill"). WRONG. Investigation (owner-driven: "it is not supposed to fail"): the drafted prompt ordered
  "output the whole completed file... FIRST characters must be <!DOCTYPE html" while the splice expects
  ONLY the region — and the v2.26 engine contract reinforced the whole-file order. The 9B OBEYED both and
  was punished for it. Timeline proof: every skeleton success predates v2.26, every failure postdates it.
- Fix (both sides of the contract): skeleton builds now get an engine-owned FILL contract ("you are
  completing ONE region; never <!DOCTYPE/tags/marker; ignore any whole-file wording below") that overrides
  the drafted prompt; the drafter's skeleton directive now requires region-only prompts (never
  <!DOCTYPE-first) when a skeleton is provided.
- Verified: fresh draft under aligned contracts -> the 9B one-shotted Game of Life. GREEN attempt 1,
  550 fill tokens, 6.0s; glider rule-check passed (26 generations, correct diagonal travel).
- Lesson recorded: when a small model "fails", check FIRST whether the harness fed it contradictory
  instructions — obedience can look exactly like incapacity.

## v2.27.0 — 2026-07-08

**Report: per-attempt trail. Engine: fill marker-echo fix. Game-of-Life documentation experiment recorded.**

- **Attempt trail in the manifest** (owner report-audit): each artifact row now shows the per-attempt story
  (`attempt trail: 1:structural(8) -> 2:PASS`) instead of only the final result.
- **Skeleton fill fix:** small models ECHO the `__FILL__` marker inside their completion (observed 4/4 on
  the 9B — `// __FILL__` as a comment); a legitimate fill never contains the marker, so echoes are stripped
  before splicing.
- **Experiment (pre-registered, identical Conway's-Game-of-Life goal):**
  fable/fable: GREEN attempt 1 — 3,356 paid tokens, 49.5s end-to-end; glider rule-check passed (21
  generations, correct diagonal travel); pinned rebuild byte-identical at 0 tokens.
  fable-spec/9B-fill: FAILED 9/9 attempts across 3 rounds — after harness bugs were fixed, the residual
  cause is the 9B emitting HTML inside the pure-JS fill region ("Unexpected token '<'"). Honest finding:
  for SMALL programs the frontier one-shot is cheaper AND more reliable; the two-tier split earns its keep
  on LARGE artifacts (Tetris: 29-98k one-shot vs ~5-12k two-tier). Task-size crossover is real.

## v2.26.0 — 2026-07-08

**Owner finding: fresh-attempt duds were FORMAT failures — hard output contract cuts attempts to 1.**

- Controlled experiment (same fable Tetris spec, fair gate): 3 fresh generations needed 2/2/3 attempts —
  the banked duds were the model NARRATING the file instead of emitting it (prose preamble, no code).
  3 pinned rebuilds: 0 model calls, 0 tokens, byte-identical hash every time (pins proven end to end).
- Fix, three layers: (1) the engine wraps EVERY artifact generation in its own fixed OUTPUT CONTRACT
  ("your reply IS the file; first character = first character of the file") — never trusting drafted
  phrasing alone; (2) SALVAGE — chatter before `<!doctype` is stripped and the candidate judged instead
  of wasted; (3) webapp drafts anchor the reply's first characters explicitly.
- After (n=1): the same spec generated green on attempt 1 (4.4k tokens, 53s vs 33-95k tokens, 6-19 min).

## v2.25.0 — 2026-07-08

**Draft-time model targeting (owner design): `lathe do "<goal>" --for <class|all>`.**

- Generate the spec FOR a chosen model class up front — `frontier`, `local-large`, `local-small`, or `all`
  (saves all three variants in the workspace as plan_for_<class>.py and builds the one matching the
  configured implementer). Distinct from repair/adaptation, which is post-failure.
- Drafting primitive `draft_spec_for` (autonomy_live): one validated variant per class, saved to the
  workspace, no board/no build; profile skeleton directive now demands ONE triple-quoted literal (the
  first draft failed validation on a concatenated skeleton — validator caught it, directive tightened).
- Experiment C recorded (the missing table row): Tetris drafted DIRECTLY for the 9B -> green on attempt 1,
  ZERO feedback rounds — analyst 11.7k tokens (one-time spec), 9B fill 196 output tokens in 8.3s.

## v2.24.1 — 2026-07-08

**web_canvas_game gate: slow-tick games no longer false-fail (a WORKING 9B Tetris was refused).**

- The animation check sampled two frames 700ms apart — but correct Tetris gravity at level 1 ticks slower
  than that, so a working game read as "not animating" (found live: the 9B's gate-refused attempt was a
  playable Tetris with zero JS errors). The gate now forces movement (soft drop) and observes across a
  window longer than one tick.
- Two-tier milestone recorded: the repaired (skeleton) Tetris spec built GREEN on the local 9B — 279
  generated tokens, 9.7s, first attempt — vs 29k-98k frontier implementer tokens for fable one-shot.

## v2.24.0 — 2026-07-08

**Model-aware specs (owner design): the analyst drafts FOR the implementer in use, guided by saved
per-class standards; pins gain a model-class anchor with revalidated cross-model reuse.**

- **Per-model-class drafting standards** (`tools/model_profiles.py`, trusted data + harness-built
  classifier `tools/model_class.py`: frontier | local-large | local-small). Every draft AND repair injects
  the standard of the CONFIGURED implementer: frontier gets whole-file latitude; local-small gets
  decomposition rules, worked examples, explicit-import rules, and — for web artifacts — a MANDATORY
  skeleton (the analyst writes the working scaffold; the small model fills ONE bounded region).
- **Proven end-to-end on the real local 9B:** `lathe do "<canvas animation page>"` with the 9B configured →
  the drafter emitted a skeleton spec targeting `openai:local` → the 9B filled the region on the GPU
  (127.0.0.1:8089) → real-Chromium gate green, first pass. The same goal one-shot on the 9B previously
  failed 3/3.
- **Pins: model class as an anchor** (`.pins.index.json` sidecar — pin keys and the H1 regime compare are
  untouched; the 500-pin corpus survives). On an exact-key miss, a pin built by a DIFFERENT model of the
  SAME class for the SAME spec is ADOPTED — but only after its code re-passes the tests. Proven: two
  frontier-class model strings, second build reused the first's pin at 0 generation calls.
- **Validator: content skeletons unblocked.** `skeleton` was python-AST-scanned, auto-rejecting every HTML
  scaffold; now .py skeletons keep the exec scan while content skeletons are held to an active/exfil
  deny-list (eval/require/fetch/import(/WebSocket/...) — CSS `!important` unaffected.
- Manifest SELECTION records which class standard shaped the spec (`spec-for:local-small`).

## v2.23.0 — 2026-07-08

**The feedback loop is now the DEFAULT everywhere: a failed build auto-invokes the analyst to adjust the spec.**

- **`lathe build` auto-repair (owner rule: "if the lower model struggles, the higher model adjusts the
  spec — in every workflow").** On a failed build, the analyst rewrites the plan from its banked failure
  evidence and the SAME implementer retries the repaired spec (`<plan>_repaired.py`; original preserved).
  One bounded round; `LATHE_REPAIR=0` disables; `--json` stays primitive-only; an INOPERATIVE (environment)
  failure is never "repaired". Every promoted workflow that builds inherits this. Proven live: a plan with
  a wrong test (`double_it(2)==5`) failed, the analyst corrected exactly the bad assert, rebuild green.
- **Fix: repair now reads the per-goal fail bank.** Function failures bank under the workspace
  (`OUT_DIR/_fn_fails/`) since v2.20, but the repair feedback reader still looked only in the legacy
  `tools/_fn_fails` — repairs ran on empty evidence for workspace builds.
- **Fix: manifest_contract gate de-flaked.** Probes located "their" manifest by mtime with a 1s slack;
  back-to-back probes in the same second (full-suite timing) could read their PREDECESSOR's manifest and
  fail with wrong-content verdicts (T2b/T2c "outcome wrong", "KeyError: analyst"). Now exact
  set-difference: only a file that did not exist before the probe counts. 5/5 clean suite runs (was ~1-in-3
  flaky).

## v2.22.0 — 2026-07-08

**`lathe repair <plan>` — the two-tier feedback loop as a first-class command.**

- The analyst reads a failing plan plus its banked failure evidence (`_fn_fails/` + NEW: the artifact
  fail bank `_artifact_fails/`) and rewrites the SPEC so the CURRENT implementer can succeed. For whole-file
  artifacts it is taught the skeleton pattern: the analyst writes the working scaffold (loop/wiring — what
  small models break) and leaves ONE `__FILL__` region for the implementer. Writes `<plan>_repaired.py`;
  the original is preserved for A/B. Rewritten plans are validated as DATA before saving.
- Motivation (live experiment): the local 9B, given fable's Tetris spec, passed all 14 STRUCTURAL asserts
  3/3 times and failed the real-browser gate 3/3 times (frozen canvas, null-rotation crashes) — code that
  LOOKS right but doesn't RUN, caught only by the behavioral gate. `repair` is the missing path from that
  evidence back to a spec the small model can execute: architect-model + free-labor-model + gate.

## v2.21.0 — 2026-07-08

**Report completeness pass: every data point a run produces is now in its manifest.**

- **Run-scoped merge (integrity fix).** Engine metrics rows carry `parent_run` (the spine token); the
  manifest merges ONLY its own builds. Previously the time-window merge absorbed a CONCURRENT process's
  builds into the wrong run's report.
- **The assert checklist is rendered.** Each artifact/function row lists the actual checks the spec pinned
  (parsed from the plan as data, never executed) — "structural(14)" now shows the 14 things it means.
- **Attempts + size per artifact** (`attempt 1`, `11151b`), and on failure a pointer to the banked
  candidates in `_artifact_fails/`.
- **SELECTION records the goal-router decision** (`goal-router -> webapp, <workspace>`) instead of
  "- not reached -"; analyst contributor splits draft vs repair calls.
- **A refused run names its cause.** The blocking workflow step is recorded as a gate verdict
  (`workflow BLOCKED: step ... rc=N`) — outcome no longer reads "REFUSE - reason: None".
- Emitter 1.2.0.

## v2.20.2 — 2026-07-08

**INOPERATIVE closes end-to-end: the autonomy loop halts on a broken gate env instead of "repairing" the spec.**

- v2.20.1 made the ENGINE honest about a broken browser env; this closes the REST of the class in one sweep:
  `engine_build` surfaces the INOPERATIVE verdict upward, and the `do`/`chat`/auto loop HALTS immediately with
  the environment fix instruction — no analyst repair calls (a rewrite can't fix a browser), no Rule-of-Three
  escalation of a blameless plan, no repeat builds into a dead gate. Verified end-to-end: broken env =
  1 build → halt with instructions; healthy env = green.

## v2.20.1 — 2026-07-07

**Functional gate joins the tri-state contract: a broken browser env is INOPERATIVE, never a spec failure.**

- A functional (Playwright) gate whose INFRASTRUCTURE fails — browser executable missing/locked, playwright
  absent, launch failure — is now classified INOPERATIVE by a harness-built triage module
  (`tools/func_gate_triage.py`): the gate re-runs on the SAME candidate (transient locks clear; no wasted
  model calls), and if it stays broken the build stops with an honest environment verdict ("the SPEC is not
  at fault; fix the environment") instead of burning every attempt and feeding the analyst repair loop
  misleading spec-failure feedback it cannot fix. Verified both ways: a deliberately-broken browser path
  yields INOPERATIVE after 1 model call; a healthy env builds the same plan green.

## v2.20.0 — 2026-07-07

**Per-goal workspaces, web goals build real browser apps, polyglot (JS) function lane, full-clarity run report.**

- **Per-goal workspaces.** `lathe do "<goal>"` now creates `goals/<slug>_<stamp>/` and everything the goal
  produces — the drafted plan, module, artifacts, pins, fail bank, run report — accumulates there. The
  tree stays clean; a goal is one folder. Routing (slug + focus) is harness-built (`tools/goal_router.py`).
- **Web goals produce actual pages/apps.** The `do` drafter routes browser-shaped goals (html/page/ui/
  game/dashboard/…) to a new `webapp` focus that drafts an ARTIFACTS plan: the model writes ONE complete
  HTML file, gated by structural asserts AND a real-Chromium behavioural gate (Playwright). Proven live:
  `lathe do "html snake game"` → a playable, browser-verified game in its workspace.
- **Trusted functional-gate registry (`tools/func_gates.py`).** Model-drafted plans cannot carry raw gate
  code (the validator refuses it — plans are data). Instead a plan names a gate (`"functional_ref":
  "web_canvas_game"`) and the engine resolves it from this hand-authored, CORE_INFRA-protected registry.
  Unknown ref = build refused, fail closed. Gates: `web_page`, `web_canvas_game`.
- **Polyglot: JavaScript function lane (#60).** A plan function may declare `"lang": "js"`: the implementer
  writes JS, its tests EXECUTE under `node` (subprocess, secret-scrubbed env) and must pass, and the
  function pins (lang-suffixed key; the python pin corpus is untouched) into `MODULE_NAME.js`.
  Python-AST gates (mutation/adversarial/regression-proof) are declared N/A per JS function — loudly,
  never silently skipped. Validator holds JS tests to a deny-list (no require/import/process/eval/…).
- **Run report states everything (#59).** The manifest now records and renders: workspace, workflow,
  thinking dial, analyst-as-contributor with MEASURED draft tokens (the drafter's request_spec instance
  was never hooked — analyst usage was silently uncounted while the report claimed COMPLETE), per-build
  detail (plan, model → resolved model @ endpoint, per-function tries/source, per-artifact gates, pins
  added, out dir), usage split by role, timing split (engine vs drafting/gates), and outcome artifact
  paths + pin counts. Emitter 1.1.0.
- **Fixes.** Config `model` was read before the config file applied (builds silently ignored it);
  `engine_build` hardcoded `openai:local` (mislabeling every do/auto build's model); a SKIPPED standing
  regression was recorded as FAIL in the manifest; CLI stdout forced to UTF-8 (a `→` in any command
  crashed under Windows cp1252 mid-workflow).

## v2.19.0 — 2026-07-07

**`lathe status` rewritten to show reality + practical use; new `lathe board --reset`.**

- **`status` diagnoses instead of dumps.** Output is grouped into *engine* (analyst + implementer, each with
  its effective model, host:port, and live reachability) and *project* (the plan⇄pin relationship + the
  commands that use it). A `READY to build` / `NOT ready` verdict now drives the exit code (0/1) for scripting.
- **Endpoint-override diagnosis.** When the implementer is down and `lathe.config.json` asked for a different
  endpoint, status calls out that an env var (`LOCAL_OPENAI_URL`) is overriding the config and prints the
  one-line fix — the most common "why is it down" cause.
- **Actionable hints, not dead ends.** A down analyst prints how to start the proxy; the STRICT hint is a
  runnable command (`$env:LATHE_STRICT=1`); the board line is labelled as `lathe auto`'s self-generated
  practice queue (not the user's tasks), with its last-active date.
- **Pins explained in place.** Status states the relationship (a plan IS the spec; a pin is its accepted build,
  keyed by spec+tests+model) and gives the two commands that make pins practical: `build` to regenerate at 0
  model calls, `trace` to see which model built each function.
- **New `lathe board --reset`.** Requeues orphaned `in_progress`/`blocked` tasks from an interrupted
  `lathe auto` run back to `pending` — non-destructive (`done`/`escalated` untouched).
- **Config `model` key → `LATHE_MODEL`.** `_apply_config_env` now maps a top-level `"model"` in
  `lathe.config.json` to the implementer default, so one config file can drive both roles.

## v2.18.0 — 2026-07-04

**Capstone tail — the four tracked items from v2.17.0, finished.**

- **#18 H3 — live review decider now RECORDS who-fired.** `cmd_review`'s decider (lens pick + license-gated
  auto-spawn) now calls `persona_orchestrator.record_run` when explore/exploit is enabled, appending
  considered/fired rows to the usage ledger. Combined with v2.17.0's `update_grades()` (H2), the grade loop
  is now connected end to end: the review path feeds the ledger, which feeds verified grades. (Honest scope:
  the lens *selection* is still word-match; UCB1 governs the additive auto-spawn — swapping the primary
  selector to `select_live` is a larger architectural change left as a separate proposal.)
- **#19 M1 — manifest selection/goal populated.** `run_spine` exposes the in-flight manifest via a
  module handle; `cmd_do` calls `set_goal`, `cmd_review` calls `set_selection` (personas + lenses + `why`).
  The record's "who/what" block is no longer always empty. Verified: `do` records `intake.goal`.
- **#20 — adversarial-synth ON by default under STRICT** (owner greenlit). A STRICT build now arms adv-synth
  automatically (explicit `LATHE_ADV_SYNTH=0` still forces it off). Combined with v2.17.0's discrimination
  fix (a probe must call the function under test), the gate is both on-by-default and harder to dodge.
- **#21 — docs counts.** `env_catalog` `LATHE_ADV_SYNTH` default reflects strict-on; README version + gate
  count fixed (v2.17.0). Reviewer-authored `docs/CLI_REFERENCE.md` env/gate counts corrected in the public
  export.

## v2.17.0 — 2026-07-04

**Capstone-review fixes (PR #16 / issues #17, #19, #20, #21).**

- **#17 (HIGH) — CLI regressions from Phase-2a promotion, fixed.** Bare-command promotion bound every
  placeholder to the same joined arg string, so `lathe review auto <file>` became `review auto auto <file>`
  → BLOCKED, and `build <stem>`'s `trace {plan}` step mis-resolved the stem → BLOCKED on a green build.
  `_run_workflow` now: (a) runs the PRIMITIVE-FIRST step as the operator's **original argv verbatim**
  (identity — no re-template, no double-bind), and (b) binds `{plan}` to the first positional arg for
  enforcement steps. `cmd_trace` now resolves a bare stem via `_resolve_plan` like `cmd_build`. Verified live:
  `review auto <file>` and `build <stem>` (build→trace→checkpoint) both run clean.
- **#20 — adversarial-synth admitted vacuous asserts, fixed (through the harness).** `admit_cases` gained a
  DISCRIMINATION check: a probe must actually CALL the function under test (`fname(` in the assert), so
  `assert True` / `assert 1==1` / `assert True # not a real test` are rejected instead of counted as
  coverage. Rebuilt under STRICT incl. mutation. (The `needs_adversarial` broadening + default-on-under-STRICT
  the review also suggests are owner-decision enhancements, tracked on #20.)
- **#19 M2 — manifest self-hash integrity bug, fixed.** If the JSON write succeeded but the `.md` render
  raised, `finalize` rewrote the JSON as `partial:true` **without recomputing the hash**, invalidating the
  self-hash. Now the already-written valid JSON is left intact (only the `.md` failed); a partial stub is
  written **only** when the JSON itself failed, and then the hash is recomputed over the partial state.
  Verified: an `.md`-write failure leaves `partial:false` + a valid self-hash.
- **#21 docs — stale counts.** `README` version `v2.2.4 → v2.16.0`, "Six standing gates → Ten". The
  `review auto <files>` form documented as primary is correct again now that #17 is fixed.

**#18 (HIGH) — work-based grades wired + fallback.** `persona_orchestrator.update_grades()` (new) turns the
usage ledger into verified grades via `finding_score`+`grade_update` (previously DEAD code — no live callers)
and writes `grades.json` after each run; a confirmed-work persona now grades above the cold-start prior
(verified: 0.8). `select_live` returning empty now FALLS BACK to the scored word-match path instead of
yielding zero auto-spawned experts. Remaining #18 piece (tracked): routing the live *lens* decider
(`lathe.py`) through `select_live` so normal `review` runs record who-fired/confirmed — that feeds the grade
loop end to end and changes the primary review path, so it lands as its own careful pass. **#19 M1**
(`set_selection`/`set_goal`/`add_model` from the deciders) also tracked.

## v2.16.0 — 2026-07-04

**Review close-out punch list (PR #15): persona default-on + property-based sampling.**

- **#1 — persona explore/exploit is now ON BY DEFAULT** (validated 143/143 reachable, PR #13). The
  `persona_orchestrator` UCB1 selector + usage-ledger/grade **recording** run out of the box; the old
  word-match path (which left ~99/143 personas unreachable) is retired as the default. Explicit opt-out:
  `LATHE_PERSONA_UCB=0` or config `personas.explore_exploit=false`. Graceful-degrade fallback unchanged.
- **#2/#3 — property-based sampling replaces the fixed-sample oracle.** New pinned `pbt_sample.py`
  (`adversarial_strings` — a deterministic library of structural bypass classes: `;`-packed statements,
  `#`-comment injection, whitespace, NUL; `sample_inputs(seed, n)` — seeded, reproducible input generation
  that always covers those classes + the fixed anchors). `mutation_equiv.equivalent_over_samples` now
  broadens its differential probe with `sample_inputs(1337, 24)` (fixed seed → still deterministic), so a
  mutant that differs only on a structural-string class the old fixed 15-probe set missed is no longer
  wrongly excluded. Honest scope: full *semantic* test-generation for arbitrary functions remains
  analyst-driven (the adv-synth gate, v2.13.0); this delivers the deterministic input-generation core.
- **Gate robustness:** the manifest/spine/tristate acceptance gates now force UTF-8 on their own stdout —
  under the engine's cp1252-piped capture a unicode `print` inside a probe was crashing the gate mid-run and
  reading as a spurious regression failure (same class as the run_gates fix in v2.15.0). Now all captured
  gates are cp1252-safe.
- Harness-built (`pbt_sample` via self-proxy; `mutation_equiv` regenerated). Hand-edited: gate UTF-8 guards,
  `persona_orchestrator.is_enabled` default flip.

## v2.15.0 — 2026-07-04

**#12 Phase 2b complete — U1 rollout to all gates, U3 engine-bypass seal, H1 pin gate-regime versioning.**
Finishes the operating-contract hardening tail. `hreview` structured-output is moot — a promoted `review`
emits a per-run manifest (Phase 0/2a) which is the structured findings record.

- **U1 rolled out** (the tri-state `gate_tristate` primitive from v2.14.0, now applied across the gates):
  - **glue gate** — the `except Exception: pass` fail-open is closed: a gate *armed but errored* is
    INOPERATIVE (blocks under STRICT), distinct from *module absent* (legacy opt-out).
  - **mutation gate** — wrapped fail-closed: scoring that crashes is INOPERATIVE, refused under STRICT
    instead of silently skipping.
  - **run_gates** — a gate subprocess that can't run (spawn error/timeout) or crashes (traceback, no clean
    summary) is labelled INOPERATIVE and always fails the standing regression closed; a **missing** gate file
    already FAILs (v2.10). Also: run_gates now forces UTF-8 on its own stdout/stderr — a gate summary line
    with a non-latin1 char was crashing `print` under the engine's cp1252-piped capture, killing the
    regression mid-run and rolling back a green build (a real latent bug this surfaced + fixed).
  - assumption gate was already fail-closed (`except: sys.exit`) — unchanged.
- **U3 — around-the-spine engine bypass sealed (WARN-FIRST, owner's choice).** `lathe build` mints
  `LATHE_SPINE_TOKEN` before it spawns the engine; a bare `python engine_v2.py <plan>` has no token → it ran
  around the operating contract (no manifest, no phases) → the engine prints a loud NOTE and records
  `spine_bypassed:true` in metrics, but still runs. `LATHE_ENGINE_REQUIRE_TOKEN=1` flips it to a hard refuse.
- **H1 — pin gate-regime versioning.** Pin re-verification (re-run tests vs pinned bytes on replay) already
  existed; H1 adds a `.pins.regime.json` sidecar recording the gate regime each pin was verified under
  (pinned `regime.py`: `regime_signature` + `regime_covers`, harness-built under STRICT). On replay a pin is
  honoured only if its regime **covers** (is at least as strict as) the current one; a pin from a genuinely
  **weaker** regime is RE-GATED (rebuilt), not trusted. Unstamped pre-H1 pins are **grandfathered** (stamped
  at current regime on first reuse) so H1 applies going forward without a full-corpus rebuild.
- **Gate-probe isolation** (`LATHE_CE_DIR`): the manifest/spine acceptance gates count files in the manifest
  dir; running INSIDE a build, the outer build + sibling gates polluted the count. Both gates now isolate
  their probes into a private temp dir (inherited by spawned children), making them deterministic under
  nested concurrency.
- Harness-built under STRICT (first-pass): `regime.py`. Hand-edited CORE_INFRA (called out): `engine_v2.py`
  (U1 glue/mutation, U3 token, H1 sidecar + regime check), `lathe.py` (token mint), `qa/run_gates.py`,
  `qa/spine_gate.py` + `qa/manifest_contract_gate.py` (isolation), `tools/manifest.py` (`LATHE_CE_DIR`).

## v2.14.0 — 2026-07-04

**#12 Phase 2b / U1 — gates fail CLOSED, not open** (reviewer's headline structural finding). A gate whose
probe couldn't run (sandbox import fail, timeout, OOM) used to `except: return False`-as-pass — a gate that
*cannot run* reported green. Gates now carry a tri-state verdict; an internal error is INOPERATIVE, never a
silent pass. Owner-decided rollout: **STRICT-first** (INOPERATIVE blocks only under `LATHE_STRICT`; non-strict
keeps today's behavior).

- **Pinned decision core** `gate_tristate.py` (harness-built under STRICT, 3/3 first-pass incl. mutation):
  - `classify_gate(raw, errored)` → `pass`/`fail`/`inoperative` — an error or indeterminate result maps to
    INOPERATIVE, not pass.
  - `canary_trustworthy(pos_passed, neg_passed)` — a probe is trusted only if a known-good control passes AND
    a known-bad control is caught; a miscalibrated probe (either canary wrong) → untrusted → inoperative.
  - `gate_blocks(verdict, strict)` — FAIL always blocks; INOPERATIVE blocks under STRICT only; an unknown
    verdict fails closed under STRICT.
- **First fail-open closed: `spec_lint`** (the exact one the reviewer named). `_stub_survives` was refactored
  to a tri-state `_stub_result` (`survived`/`killed`/`inoperative`) and `lint_function` now runs a **sandbox
  canary** (a trivially-true assert must pass, a trivially-false assert must be caught) before trusting any
  result — if the sandbox is broken the whole lint is `inoperative`. The engine's `LATHE_LINT_SPEC` gate maps
  the verdict through `gate_blocks`, so under STRICT an unverifiable spec-lint refuses the build instead of
  shipping blind. Old bool `_stub_survives` kept as a back-compat shim.
- **Acceptance gate** `qa/tristate_gate.py` (standing regression, now 10 checks): V1 error→INOPERATIVE, V2
  canary gating, V3 blocking policy, V4 **the real fail-open closed** — a monkeypatched broken sandbox makes
  `lint_function` return `inoperative` (was a silent pass) and blocks under STRICT, V4b operative path
  unchanged.
- Verified: a healthy STRICT build still passes (canary green, no false INOPERATIVE). Rollout to the remaining
  gates (run_gates subprocess errors, mutation/assumption/glue) follows the same primitive incrementally.

## v2.13.1 — 2026-07-04

**#12 Phase 2a follow-up — the manifest names its resolved workflow** (reviewer's minor gap on v2.12.0). A
workflow-backed command ran its steps (they landed in `work.steps`) but the intake header left `intake.skill`
and `intake.workflow_steps` `null`, contradicting `MANIFEST_DESIGN.md §1`. Now `run_spine` records the
resolved workflow name + its ordered step labels in the intake header the moment promotion engages
(`manifest.set_workflow`). New acceptance probe **T7** (manifest_contract_gate, now 6/6): a promoted `review`
manifest carries `intake.skill == "code-review"` and a non-empty `intake.workflow_steps`. Verified in-process
and by the gate. Trunk-only change (`lathe.py` promotion site, `manifest.py` skeleton + setter); no plan rebuilt.

## v2.13.0 — 2026-07-04

**Issue #11 — adversarial test synthesis as a GATE.** The harness now finds its OWN coverage gaps: before a
gate-critical function may pin, the analyst (a capable adversary) synthesizes bypass probes and the candidate
must survive them. Every fail-open the external reviewer found was a harness-built module whose tests didn't
cover the adversarial case — this closes that loop internally. Opt-in: `LATHE_ADV_SYNTH=1`.

- **Pinned decision core** `adv_synth.py` (harness-built under STRICT, 3/3 incl. mutation):
  - `needs_adversarial(kinds, plan, policy)` — which functions face synthesis (`off`|`gates` default|`all`;
    `gates` = kind `gate` or a gate/valid/strict/guard plan name).
  - `admit_cases(cases, example_tests, min_cases)` — **fail-closed** admissibility: zero cases, prose,
    non-asserts, or copies of the example tests are REFUSED (symmetric to the v2.9.0 zero-cases guard); a lazy
    analyst cannot rubber-stamp.
  - `adv_verdict(ran, failures, admitted)` — **tri-state honest**: an admitted probe that did not run is
    `INOPERATIVE` (never a silent pass), any failure is `FAIL`, else `PASS` (the #12-U1 direction).
- **Engine gate** (`_adv_synth_gate`, hand-edited, fires at the pin point after the mutation gate): synthesizes
  with the ANALYST model (`LATHE_ADV_MODEL`, default `claude`) — not the implementer — runs each admitted probe
  against the candidate via the real sandbox, and refuses the pin on FAIL/INOPERATIVE. Analyst usage is
  role-attributed in the run manifest (#12 Phase 0).
- **Calibration (the hard part, solved):** the adversary is given the function's EXACT SPEC and instructed to
  probe ONLY for spec violations — never to assert behavior the spec doesn't mandate. Without this, probes
  over-reach (a spec that *allows* `.` gets a probe demanding it be rejected → false failure); with it, a
  correct allow-list impl survives while a naive deny-list impl is caught on real gaps (`\\`-absolute + UNC
  paths). Both directions verified live.
- Env: `LATHE_ADV_SYNTH` / `LATHE_ADV_POLICY` / `LATHE_ADV_MIN` / `LATHE_ADV_MODEL` (documented in
  `env_catalog.py`). Off by default; a future release folds it into the STRICT umbrella once calibration is
  proven across the catalog.
- **Two test-authoring bugs the harness caught in MY OWN plan during this build** (logged for honesty): the
  `admit_cases` tests asserted a kept list survives alongside a REFUSED verdict (contradicts the spec — refuse
  returns `[]`); the throwaway probe plan used invalid `\x`/`C:\` escapes. The gates refused to pin against the
  buggy specs — the discipline catching its author.

## v2.12.0 — 2026-07-04

**Operating contract Phase 2a — the 19 per-invocation WORKFLOWS + bare-command PROMOTION** (issue #12;
specs: `docs/operating-contract/workflows/*.md` on PR #7). Plus the reviewer's U2 structural fail-open, closed.

- **19 workflow ids** (data, `workflows.py`): build-from-goal, build-from-plan, code-review (hardened),
  clarify-goal, assumption-audit, verify-reproduce, gate-quality, trace-inspect, maintain-tree, ship-release,
  serve-api, select-grade-experts, report-triage, autonomous, sdlc-requirements, onboard-project + the
  existing bug-fix / enhancement / doc-review. Design rule: primitive-FIRST with `{args}` passthrough
  (stdout + exit code preserved; the manifest is a side-file), then only steps that ADD enforcement — the
  contract never runs the same gate twice (the engine gates its own builds internally).
- **Promotion wired into `run_spine` phase 3:** a contracted bare command now runs its per-invocation
  workflow — steps in order, halt on the first blocked, verdicts from rc via the pinned classifier (never
  model text), every step recorded in the manifest's `work.steps`. `--json` stays primitive-only (compat:
  the stable metrics object is the only stdout). Steps re-enter `main()` RAW under the guard — still exactly
  one manifest per top-level invocation.
- **Guided `code-review` workflow hardened:** its AUTO `build {plan}` step mis-bound a bare review's FILE
  target as a plan (verified: would hard-block every promoted review) — rebuilding the owning plan needs a
  human to identify WHICH plan owns the finding, so it is now a YOU checkpoint.
- **U2 closed (reviewer's structural finding, CONFIRMED): STRICT now CLAMPS, never defers.** The old
  `strict_defaults` filled-only-if-empty, so a pre-exported `LATHE_MUTATION_SCORE=0.01` or
  `LATHE_LINT_SPEC=warn` silently survived STRICT. New pinned `strict_clamp` (harness-built, first-pass
  under STRICT incl. mutation): mode keys are forced to the strict value, the numeric mutation floor is
  `max(configured, 0.5)`, and every displaced value prints LOUDLY
  (`CLAMPED: env had '0.01' below the STRICT floor`). Live-verified.
- **Recursion fail-open found & fixed during validation:** the promoted `do` workflow carries a real gate
  step; the manifest acceptance gate runs INSIDE that gate suite and probes a promoted command — the probe
  re-entered the suite → infinite regress → the engine's regression timed out and rolled back a green
  build. The acceptance gate now stubs the gate step for its probes (it asserts routing/manifest behavior,
  not gate content), breaking the cycle at the only edge that loops.
- Deferred to Phase 2b (declared, not hidden): U1 tri-state gate verdicts + canary pairs, U3 engine
  contract-token (no around-the-spine engine entry), H1 pin re-verification + gate-regime versioning,
  hreview structured findings output, and the review-path usage ledger (lands with PR #13's orchestrator).

## v2.11.0 — 2026-07-04

**Operating contract Phase 1 — the ENFORCEMENT SPINE** (issue #12; design:
`docs/operating-contract/ENFORCEMENT_SPINE_DESIGN.md` on PR #7). Bare commands now run *through* their
contract — there is no data/skill path around it.

- **`main()` split into spine + raw dispatch.** Top-level calls enter `run_spine` (the six-phase contract in
  deterministic code); the raw `_dispatch` is underscore-private and reachable only via `main`. A re-entrancy
  guard (`_LATHE_SPINE_RUN`, set by code for the dynamic extent of a run) makes inner re-entrant steps (e.g.
  `lathe flow`'s AUTO steps) run RAW under the outer spine — **exactly one manifest per top-level invocation**.
- **Guard-forge defense:** both process entries FORCE-clear the guard (same rationale as the forced
  `LATHE_VALIDATE_PLAN`), so a hostile pre-set env var cannot make the top level skip its contract. A skill
  that shells out to `lathe` gets a fresh process → cleared guard → its own full spine + manifest.
- **Thinking dial** `LATHE_THINK ∈ {casual, medium, high}` (or `--think=`, or config `thinking.level`) —
  resolved at intake by pinned `spine_core.resolve_thinking` (flag > env > config), expanded by pinned
  `depth_env` into `LATHE_TRIES` / `LATHE_SELECT_N` / `LATHE_ASSUMPTION_POLICY` stamps applied with
  `setdefault` (an operator's explicit env always wins). Recorded in the manifest's intake row.
- **`CONTRACT_FOR`** (data, `workflows.py`): command → contract (workflow / front_end / select / gate /
  writes / argmap). Read-only commands are TRIVIAL — spine runs, phases no-op, byte-identical behavior.
  Phase-4 standing gates run after green writes where the contract says so. Workflow *promotion* (bare
  command → its multi-step workflow) lands in Phase 2 with the 19 hardened workflows; today's 6 guided
  workflows don't arg-bind safely as contracts (verified: code-review's `build {plan}` step mis-binds a
  bare review's file target).
- **Operator bypass on the record:** `LATHE_SPINE=off` (pre-process env only) runs raw but still emits a
  manifest recording `disabled-by-operator`.
- **Stress gate** `qa/spine_gate.py` (standing regression, now 10 checks): P1 guard-forge defeated, P2
  exactly-one-manifest under re-entry, P3 skill-subprocess gets its own spine, P4 bypass recorded, P5
  single-raw-path static invariant.
- **Fail-open found & fixed by the new gates during validation:** the engine fell off the end of the script,
  so a build that FAILED gates / got rolled back still **exited 0** — `lathe build` (plain path) read green
  on red. The engine now exits `0 iff build_ok`. (Caught because the spine's manifest showed
  `outcome: pass` beside `gates.all_pass: false` — the record contradicting the exit code.)
- Harness-built under LATHE_STRICT (3/3 first-pass incl. mutation): `spine_core.py` (resolve_thinking,
  depth_env, contract_of). Hand-edited CORE_INFRA (called out): `lathe.py` (spine/dispatch/guard),
  `engine_v2.py` (exit code), `workflows.py` (CONTRACT_FOR data), `env_catalog.py` (LATHE_THINK/LATHE_SPINE),
  both acceptance gates (guard-clear at library entry).

## v2.10.0 — 2026-07-03

**Operating contract Phase 0 — the per-invocation MANIFEST** (issue #12, owner-set priority; design:
`docs/operating-contract/MANIFEST_DESIGN.md` on PR #7). Every CLI invocation now emits a complete, un-skippable
run record to `docs/ce/<run_id>.manifest.{json,md}` — the evaluation instrument the rest of the contract builds on.

- **Un-skippable emission (structural).** `lathe.py main()` wraps the single dispatcher chokepoint:
  `Manifest.begin()` writes a `partial:true` stub atomically before any work; `finalize()` runs in a `finally`,
  so return codes, raises, `SystemExit`, gate aborts and Ctrl-C all still emit. Bare `lathe "<goal>"` is stamped
  `routed_via:"bare-goal"` — through the contract, provably. Skills/workflows can only append content.
- **Analyst-token gap closed, all three layers** (v2.9.1 closed part of L2):
  - *L1* `claude_proxy.py` non-stream path runs the CLI with `--output-format json` and returns **real measured
    usage** (incl. cache tokens, `token_source:"measured"`) instead of hardcoded zeros; an unparseable/legacy
    reply is tagged `"unmeasured"`, never silently zero.
  - *L2/L3* engine: per-ROLE buckets (`tok_by_role`: implementer/judge; analyst reports via `request_spec`'s new
    `USAGE_HOOK`), one accrual path for every branch, role threaded through `call_model`. Metrics row + manifest
    carry the split.
  - **Completeness invariant** (pinned `manifest_core.role_usage`): a role with calls>0 but tokens==0 makes the
    manifest read `attribution: INCOMPLETE (n uninstrumented)` — the gap can never silently regress (gate asserts
    the string "NOT INSTRUMENTED" never reappears).
- **Dollar cost**: versioned `pricebook.py` (list prices) + pinned `manifest_core.imputed_cost` — real `$0`
  subscription/local spend is distinguished from *imputed* list-price cost, per role, 6dp.
- **Integrity**: pinned `manifest_core.manifest_hash` — deterministic self-hash with the hash field blanked;
  `partial` flag marks crash-time records.
- **Acceptance gate** `qa/manifest_contract_gate.py` (standing regression, runs on every build): T2 un-skippable
  (return/raise/SystemExit), T3 structural completeness + self-hash verify, T4 analyst-instrumented + gap-visible,
  T5 role-split imputed cost exact, T6 bare-goal routed through the contract. T1-full/T7/T8 remain external
  reviewer probes.
- **Fail-open fixed in passing** (named in #12): `qa/run_gates.py` silently `continue`d past a **missing gate
  file** and still printed "regression clean" — a registered-but-absent gate is now a FAIL. Also fixed: the
  engine's regression runner decoded gate output as cp1252 and crashed on UTF-8 (now pinned utf-8 + guarded).
- Harness-built under LATHE_STRICT (3/3 first-pass incl. mutation gate): `manifest_core.py`. Hand-edited
  CORE_INFRA (called out per owner standard): `lathe.py` dispatcher wrap, `engine_v2.py` role accounting,
  `claude_proxy.py` L1, `qa/run_gates.py`, spine `tools/manifest.py` + data `tools/pricebook.py`.

## v2.9.1 — 2026-07-03

**Build report — honest analyst-token accounting** (PR #7 issue #10). The report's token line always said the
analyst was "NOT INSTRUMENTED," making the savings figure look complete when it counted only the implementer
tier. Now: (1) engine model calls (implementer + any claude-tier calls) **sum reported `usage` tokens** when
the endpoint returns them (new `_accrue_usage`, applied to the claude path; the openai path already did); (2)
the analyst line is **honest and conditional** — when the analyst is a human or a subscription CLI that
returns no usage, it reads *"UNTOKENED this run … the tier totals count the IMPLEMENTER only, so true cost is
understated"* rather than implying completeness. (Full spec-authoring instrumentation — threading upstream
`lathe do`/`sdlc` analyst usage into the report — and a `$`-cost column are noted as follow-ups.)

## v2.9.0 — 2026-07-03

**PR #7 gate stress-test — 4 fail-open gate bypasses closed** (independent reviewer, executed against the real
pinned functions; issues #4/#5/#6/#8). Each let a build that should refuse slip through:
- **#6 assumption gate (headline guarantee)** — an assumption the auditor left unranked/garbled normalized to
  `med` and, under the shipped default `high` scrutiny, silently did NOT block. Now **fail-closed**: unknown/
  empty/garbled materiality → `high`, and `blocking_assumptions`/`unconfirmed_blockers` treat any non-canonical
  label (`'medium'`, `'critical'`, missing) as `high`. Labeling drift can no longer disarm the gate. (harness)
- **#4 gate-the-glue** — F1: `count_glue_lines` counted physical newlines, so `;`-packed statements slipped
  under `LATHE_GLUE_MAX` — now counts **AST statements** (`a=1; import os; os.system(...)` → 3, not 1). F2:
  any non-empty `INTEGRATION` (even `pass`) counted as "exercised" — the engine now requires the block to
  contain an **`assert`**. (harness + engine)
- **#5 test-kind** — the substring classifier let a **comment** satisfy a required kind (`# never raises` →
  `error`, fail-open) and missed real tests. Now **strips comments before matching** and recognizes
  `sorted`/`reversed` as `property`. (harness)
- **#8 standing gates** — F7: docs-drift used `name not in doc_text`, so `do` read as documented inside
  `done`/`window` — now **whole-word** match (regex lookarounds, hyphen-safe). F8: the stale-file retire
  pattern was too narrow (missed `_v3+`, `_final`, `_new`, `_prev`, `_deprecated`, `(copy)`) — broadened, with
  no false positives on the current tree. (harness + core-infra)
- Issues #2 (mutation-equiv) and #3 (REST API) from the same batch were already fixed in **v2.8.1**.
  Acceptance tests extended; all gate acceptance suites + standing gates green.

## v2.8.1 — 2026-07-03

**PR #1 capstone-review — 4 code-side findings fixed** (independent reviewer, cross-adjudicated; none refuted):
- **#1 `mutation_equiv.equivalent_over_samples` was unsound as a mutation-gate input.** Two defects fixed
  through the harness: (a) two functions are now equivalent ONLY when they agree on a real **value** over the
  probe sample — error-agreement alone (a mutant that merely raises) no longer counts; (b) the equality oracle
  is **value equality**, not `repr()`, so dict key-ordering / object identity no longer cause false
  non-equivalence. Verified: both-raise → False, dict-order → True, real equivalent mutant → True.
- **#2 INTEGRATION runner inherited the full env** (`engine_v2.py`): the plan-authored integration test now
  runs with the **same secret-denylist scrub** as `_func_test` (previously only the functional path scrubbed).
- **#3 docker sandbox** (`sandbox.py`): the container is now **named and `docker kill`ed on timeout** (the
  `docker run` client dying didn't stop the container — a runaway kept burning CPU); and the docker→subprocess
  **downgrade now warns loudly** instead of silently weakening isolation. (Docker runtime verification needs a
  daemon — not run here; static fix only.)
- **#4 REST API** (`lathe_api.py`): the build subprocess **no longer inherits `LATHE_API_TOKEN`** or any
  secret-hinted var (denylist scrub); a gate **refusal** is now `status:done`+`build_ok:false` (not `failed`,
  which is reserved for a job error) — matching `API.md`; the jobs dict is **bounded** (200, oldest evicted);
  and a value-less `--bind` no longer `IndexError`s.

Note: `mutation_equiv` rebuilt with the correctness gates (test-ack + regression-proof + lint + test-kind, 26
tests); the mutation-score-on-this-meta-function itself doesn't clear 0.5 with the local model (some survivors
are plausibly equivalent mutants — fittingly), so it isn't self-mutation-gated. `engine_v2`/`sandbox`/
`lathe_api`/`lathe.py` are hand-maintained CORE_INFRA per doctrine. API + mutation-equiv acceptance tests green.

## v2.8.0 — 2026-07-03

**REST/HTTP API (v0)** — the PR#1 reviewer's proposal, built full per owner direction (a web dashboard is on
the roadmap). An **opt-in, local-first** surface for NON-agent consumers (dashboard/UI, language-agnostic
services, CI-over-HTTP); agents keep MCP. It is an *additional caller of the same gated engine* — no gate is
weakened, pins/determinism unchanged.
- **`lathe serve`** starts `lathe_api.py` (stdlib `http.server`, **no new deps**). Read-only sync endpoints
  (`GET /v1/env|plans|metrics`, `POST /v1/gate|verify|trace|review`) + async **build jobs**
  (`POST /v1/builds` → `202 {job_id}`, `GET /v1/builds/{id}` → the `build --json` object when terminal).
- **Security**: bearer-token required (`LATHE_API_TOKEN`; no token ⇒ won't start), constant-time auth,
  `127.0.0.1` bind by default (non-local bind requires a docker sandbox), every path `is_within_root`, every
  string `reject_flags`, caller `env` overrides **allow-listed** (never `LATHE_TRUST_PLAN`/`SANDBOX`/endpoints),
  `GET /v1/env` returns the catalog **never values**.
- The security-critical request logic is the harness-built pinned `api_logic.py` (`bearer_token`, `auth_ok`,
  `env_allowlist`, `classify_build_body`, `job_view`; STRICT, CRITERIA P1–P5, fable, first-try); the HTTP glue
  is `lathe_api.py`, covered by `review_tests/test_api.py` (live server, real token, real async build job).
- New docs `API.md`; new env vars `LATHE_API_TOKEN`/`LATHE_API_PORT` (documented — the env-drift gate now also
  scans `lathe_api.py`/`lathe_mcp.py`, 55 vars). `lathe serve` documented (docs-drift, 36 commands).

## v2.7.0 — 2026-07-03

**PR #1 CLI-review — 3 enhancement suggestions implemented.**
- **Canonical env-var surface + anti-drift gate (#1).** New `lathe env` prints every recognized env var —
  grouped, with role + default — from a single source of truth (`env_catalog.py`, 53 documented). New standing
  gate **`env_not_drifted`** (`qa/env_drift_gate.py`) extracts the vars the code actually reads (harness-built
  `env_logic.extract_env_vars`) and **fails the build** if any user-facing one is undocumented — so a new env
  var can't drift in silently, the same discipline docs-drift applies to commands. Gate count 6 → 7.
- **`lathe map` graceful degrade (#2).** Without `universal-ctags` it now **warns and skips (exit 0)** instead
  of hard-failing (rc 1) — the repo-map is an optional convenience, not a hard dependency.
- **`lathe build --json` (#3).** Emits a single stable JSON object (the metrics: `build_ok`,
  `functions_passed/total`, `per_function {name,ok,tries,src}`, tokens, timings), exit 0 iff `build_ok` — no
  more PASS/REUSED column drift for a CI wrapper to misparse.
- New pinned module `env_logic.py` (`extract_env_vars`, `env_drift`) built through the harness under STRICT
  (CRITERIA E1–E2), fable implementer, first-try; acceptance test `review_tests/test_env_drift.py` (units +
  the live "registry documents every code var" guard). Also documented `LOCAL_OPENAI_MAXTOK` / `LOCAL_GEN_TIMEOUT`.

## v2.6.2 — 2026-07-03

**PR #1 v2.6.1 review — 4 findings addressed** (independent reviewer, no HIGH bugs; the resolve flow verified clean):
- **#1 MED (design): an empty auto-audit no longer launders as a clean pass.** If the auditor surfaces **0**
  assumptions, the committed `<plan>.decisions.md` and the console now flag it **ADVISORY** — "auditor surfaced
  nothing ≠ human review" — and the engine prints the same warning instead of a silent pass. (A model
  self-audit that collapses its own ledger is exactly the drift the gate exists to stop.)
- **#4 LOW: the engine-side assumption gate now fails CLOSED.** Only genuine module/state absence
  (`ImportError`/`FileNotFoundError`) is opt-out; any other enforcement error when the gate is enabled now
  `sys.exit`s instead of `except: pass`.
- **#3 MED: `lathe_mcp.lathe_do` now flag-guards its `goal`** with `reject_flags`, matching its siblings
  (`build`/`verify`/`review`) — a client goal starting with `-` is refused (argument-injection consistency).
- **#2 MED: honest caveat added for test-kind.** Docs now state that kind detection is a *substring heuristic*
  (a comment/string can satisfy a required kind) that catches an *absent* kind, not a weak one — mutation-score
  is the real backstop. (ARCHITECTURE §enforcement, LATHE_CAPABILITIES.)
Acceptance test extended (empty-audit advisory). Fixes are in the hand-maintained engine/CLI/MCP wiring (CORE_INFRA) + docs.

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
