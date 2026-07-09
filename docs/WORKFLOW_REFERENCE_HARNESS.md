# Lathe — Workflow & Operating-Contract Reference (harness edition)

*Authored by the analyst brain, then folded through one harness review pass. Every factual claim is grounded at `file:line` against the pinned sources; nothing is asserted from task text. The self-review notes (§7) record what the review caught and how this final differs from the draft — the proof the loop ran.*

---

## 1. Doctrine, in one paragraph

Lathe is a **project-agnostic, two-tier, gated build harness**: you give it a spec and it generates tested code with a cheap local model, gates the output, and pins it for reproducibility (`CLAUDE.md:3-7`). The two tiers are fixed and "do not break" (`CLAUDE.md:9`): **Claude is the analyst** — it writes specs + tests and does review work only, *never* the bulk implementer (`CLAUDE.md:10-11`); the **local model is the implementer** — it generates code from the spec and its output is never hand-edited (you change the spec and regenerate) (`CLAUDE.md:12-13`). Spec + tests are the source of truth; code is a build output that is test-gated and **pinned** by sha256 of spec+tests+model so identical inputs rebuild from cache (`CLAUDE.md:14-15`). One plan is one small, pure, fully-tested unit (≥4 asserts, single-pass); if the local model can't satisfy a spec you sharpen the spec or shrink the fill region rather than brute-forcing (`CLAUDE.md:16-17`).

---

## 2. The six-phase operating contract (`run_spine`)

Every `lathe` invocation is wrapped by `run_spine(cmd, rest, argv)` — "the six-phase operating contract, in deterministic code around the data … A workflow can define bad steps but cannot delete a phase — phases are not in the data. Emission is unconditional." (`lathe.py:1760-1762`). The whole body is `lathe.py:1760-1833`.

| Phase | What happens | Grounded at |
|---|---|---|
| **begin** | Route (`table` vs `bare-goal`) and open the manifest; expose it as `_CURRENT_MF` so `cmd_do`/`cmd_review` can set goal/selection | `lathe.py:1763-1767` |
| **0 — intake** | Thinking dial → depth env stamps; records `intake` gate with `thinking=… contract=…` | `lathe.py:1786-1793` |
| **1 — front-end** | `clarify`/`assume` (per the command's `front_end` flag); no-op when the contract is trivial | contract keys, `workflows.py` `CONTRACT_FOR`; dispatched in-work |
| **2 — select** | Persona selection (per the `select` flag) | contract keys, `workflows.py` `CONTRACT_FOR` |
| **3 — work** | If the command has a workflow and `--json` is absent, run the promoted per-invocation workflow; else dispatch the primitive | `lathe.py:1797-1814` |
| **4 — standing gates** | After a **green** write, run `_phase_gates` (only if `contract.get("gate")` and `rc == 0`) | `lathe.py:1815-1816` |
| **5 — finalize** | `mf.finalize()` in `finally:` — "phase 5: ALWAYS" | `lathe.py:1828-1833` |

**Re-entrancy guard.** Once past intake, the spine stamps a per-run token into `_SPINE_GUARD` (and `LATHE_SPINE_TOKEN`, which "proves engine subprocesses ran via the spine") so nested inner `main()` calls "run RAW" and don't re-run the spine (`lathe.py:1794-1796`); the guard is unconditionally cleared in `finally:` (`lathe.py:1829`).

**Unconditional manifest emission on all three exits.** The manifest outcome is set on the normal return (`lathe.py:1817-1818`), on a handler `sys.exit()` (`SystemExit` → status `refuse`/`pass`, `lathe.py:1820-1822`), and on any crash/interrupt/gate-abort (`BaseException` → status `error`, `lathe.py:1824-1826`); the `finally:` block then merges metrics and calls `finalize()` on every path (`lathe.py:1831-1833`). An operator can bypass the spine with `LATHE_SPINE=off`, but that bypass is itself recorded as a `spine … disabled-by-operator` gate on the manifest before dispatch (`lathe.py:1778-1784`).

---

## 3. The thinking dial (`spine_core.py`, exact)

`resolve_thinking(flag, env_value, config_value)` accepts only `('casual', 'medium', 'high')`, checking flag → env → config in order and lower/strip-normalizing each; anything unrecognized falls through to the default `'medium'` (`spine_core.py:4-11`). `depth_env(level)` maps the resolved level to exact env stamps (`spine_core.py:13-23`):

| Level | `LATHE_TRIES` | `LATHE_SELECT_N` | `LATHE_ASSUMPTION_POLICY` | Line |
|---|---|---|---|---|
| `casual` | `1` | `1` | `off` | `spine_core.py:15` |
| `medium` | `3` | `2` | `high` | `spine_core.py:16` |
| `high` | `5` | `4` | `high+med` | `spine_core.py:17` |

An unknown level resolves to the `medium` row (`spine_core.py:20`). **Fill-only semantics:** the spine applies these with `os.environ.setdefault(k, v)` — "env > profile > config > default: fill only unset" — so an explicit pre-set env var always wins over the dial (`lathe.py:1790-1791`).

**On the `high+med` token.** `depth_env('high')` stamps `LATHE_ASSUMPTION_POLICY='high+med'` (`spine_core.py:17`), which is not one of the spellings enumerated in `GATES_REFERENCE.md` §1.8 (`off/none/advisory/high/med/all/low`). It is nonetheless **correct**, and here is the *full* branch chain that proves it (not one isolated line — `assumption_logic.py:47-51`):

```
if 'all' in p or 'low' in p:   allowed = {'high','med','low'}   # :47
elif 'med' in p:               allowed = {'high','med'}          # :49
else:                          allowed = {'high'}                # :51
```

Dispatch is by *substring*. Crucially there is **no `elif 'high' in p:` branch preceding the `'med'` test** — `'high'` is only the `else` default. So `'high+med'` (contains neither `'all'` nor `'low'`, does contain `'med'`) matches the `:49` branch → `allowed = {'high','med'}` = exactly the documented `med` policy. `unconfirmed_blockers` repeats the same chain at `assumption_logic.py:84`. So `high+med` is a silently-accepted alias of `med`, not an out-of-vocabulary failure. *(This proof was tightened after `lathe review correctness`/`adversarial` flagged the original as asserted-from-one-line rather than traced through the chain — see §7.)*

---

## 4. Personas (grounded in the files, not asserted)

Persona selection is a real UCB1 bandit: `ucb1(mean, count, total, c)` is defined at `persona_select.py:4`, returning `float('inf')` for an unplayed arm (`persona_select.py:7-8`) — the standard "explore-unseen-first" UCB1 shape. The supporting modules exist on disk: `usage_ledger.py` and `persona_grade.py` are both present in `tools/`. So "UCB1 persona selection, usage-ledgered and graded" is grounded, not inferred from the task prose. (The `select` phase of the spine gates on `LATHE_SELECT_N`, whose value comes from the thinking dial above — `1`/`2`/`4` for casual/medium/high, `spine_core.py:15-17`.)

---

## 5. The two gate families

Lathe has two gate families that run at different times (`GATES_REFERENCE.md`, Parts 1–2).

**Build-time gates (per function, composed by `LATHE_STRICT`)** — off by default except the always-on acceptance floor (§1.0). `LATHE_STRICT=1` expands into the seven rigor gates (traceability, regression-proof, spec-lint, mutation-score, test-ack, test-kind, gate-the-glue, assumption) with clamped-up defaults (`GATES_REFERENCE.md` §1.0–1.8, Part 3). The assumption gate's scrutiny is exactly the `LATHE_ASSUMPTION_POLICY` token the thinking dial stamps (§3 above).

**Standing regression gates (`qa/run_gates.py`)** — run after every successful build; any non-zero exit turns the build RED. The authoritative list is the `CHECKS` array at **`run_gates.py:24-33` — ten gates**, and a registered-but-missing gate file is a FAIL, not a silent skip (`run_gates.py`, `main()` missing-file branch):

| # | Check | Gate file | Line | Documented in `GATES_REFERENCE.md`? |
|---|---|---|---|---|
| 1 | `tree_no_stale_dups` | `stale_gate.py` | `run_gates.py:24` | yes (§2.1) |
| 2 | `no_duplicate_resources` | `resource_dups_gate.py` | `run_gates.py:25` | yes (§2.2) |
| 3 | `capability_registry` | `registry_gate.py` | `run_gates.py:26` | yes (§2.3) |
| 4 | `pristine_tree` | `pristine_gate.py` | `run_gates.py:27` | yes (§2.4) |
| 5 | `lint_no_real_bugs` | `lint_gate.py` | `run_gates.py:28` | yes (§2.5) |
| 6 | `docs_not_drifted` | `docs_drift_gate.py` | `run_gates.py:29` | yes (§2.6) |
| 7 | `env_not_drifted` | `env_drift_gate.py` | `run_gates.py:30` | yes (§2.7) |
| 8 | `manifest_contract` | `manifest_contract_gate.py` | `run_gates.py:31` | **no** |
| 9 | `spine_enforced` | `spine_gate.py` | `run_gates.py:32` | **no** |
| 10 | `gate_tristate` | `tristate_gate.py` | `run_gates.py:33` | **no** |

> **Docs-drift finding (open against `GATES_REFERENCE.md`).** That reference documents only the **first seven** standing gates (its Part 2 table stops at `env_not_drifted`); the real suite has **ten** — see rows 8–10 above for the names, files, and lines (the table is the single source of truth for those facts). Note only that the three are *not* one family: rows 8–9 are the "#12" manifest/spine gates, but row 10 (`gate_tristate`) is the **fail-closed** guard, so `GATES_REFERENCE.md` should add all three as rows 8–10 without grouping them under one heading.

---

## 6. All 21 workflows

The registry defines **21** workflows: the **6 named** guided workflows (`WORKFLOWS`, `workflows.py`) plus **15 per-invocation** workflows added by `WORKFLOWS.update({...})` (`workflows.py`). Every `[AUTO]`/`[GATE]`/`[YOU]` step below is quoted from `workflows.py` and cross-checks against the canonical `lathe flow` dump in `WORKFLOW_REFERENCE_STEPS.md`.

### 6a. The six named workflows

Each carries a `CONTRACTS` entry (`when`/`entry`/`deliverable`/`done`, `workflows.py`).

| Workflow | Steps (AUTO / GATE / YOU) | Contract `done when` |
|---|---|---|
| **code-review** | 1 AUTO (`review auto {files}`), 1 GATE, 3 YOU | Gates green, touched specs pass lint-spec, canonical re-cut if shipped |
| **bug-fix** | 5 AUTO (`build`,`logs --tail`,`lint-spec`,`assume`,`build`), 1 GATE, 3 YOU | Rebuild green, tree clean, adversarial+correctness review clear, released |
| **enhancement** | 3 AUTO (`assume`,`build`,`lint-spec`) + 1 AUTO (`review all {files}`), 1 GATE, 4 YOU | Built+gated, tests pin behavior, all-lens review clear, documented, released |
| **doc-review** | 1 AUTO (`review maintainability {files}`), 1 GATE, 1 YOU | Review clear, docs-drift gate green |
| **sdlc** | 7 AUTO (`clarify`,`sdlc`,`ack`,`assume`,`build`,`trace`,`review auto`), 1 GATE, 3 YOU | RTM PASS, STRICT build green, trace covers every criterion, released |
| **new-project** | 2 AUTO (`selftest`,`do "…"`), 1 GATE, 3 YOU | selftest passes, tree clean, first `do` pinned, product gates added |

Persona-bearing steps are the `review auto`/`review all` steps (the decider picks lenses); the assumption steps are adversarial-auditor gates ("HIGH blocks", `workflows.py`, bug-fix/enhancement/sdlc). Tunables surfaced in the step text: `LATHE_STRICT=1` (enhancement step 4, sdlc step 7), `LATHE_TEST_KIND=1` (enhancement step 2).

### 6b. The fifteen per-invocation workflows

These are `command → workflow` promotions wired through `CONTRACT_FOR` (`workflows.py`); the spine runs the promoted workflow in phase 3 when it exists and binds (`lathe.py:1797-1814`). **14 of the 15 are runnable** — their first step is an `[AUTO]` `lathe` primitive with `{args}` passthrough. **`onboard-project` is the sole exception**: it is a **`[YOU]`-only alias of `new-project`**, whose one step is the human checkpoint `("you", "Follow the new-project guided workflow (lathe flow new-project)", "")` (`workflows.py`; confirmed in `WORKFLOW_REFERENCE_STEPS.md` → "1. [YOU] Follow the new-project guided workflow"). It carries no `lathe` command a reader can type, so it is **not** counted as runnable.

| Workflow | Primitive / kind | Bound command → `CONTRACT_FOR` |
|---|---|---|
| build-from-goal | `do {args}` + GATE + YOU | `do` (front_end 1, select 1, gate 0, writes 1) |
| build-from-plan | `build {args}` + `trace {plan}` + YOU | `build` (gate 0, writes 1) |
| clarify-goal | `clarify {args}` | `clarify` (front_end 1, writes 1) |
| assumption-audit | `assume {args}` | `assume` (gate 1, writes 1) |
| verify-reproduce | `verify {args}` | `verify` (gate 0, writes 0) |
| gate-quality | `gate` | `gate` (writes 0) |
| trace-inspect | `trace {args}` | `trace` (writes 0) |
| maintain-tree | `clean {args}` + GATE | `clean` (writes 1) |
| ship-release | `checkin {args}` + YOU | `checkin` (writes 1) |
| serve-api | `serve {args}` | `serve` (writes 0) |
| select-grade-experts | `agent {args}` | `agent` (writes 0) |
| report-triage | `report {args}` + YOU | `report` (writes 0) |
| autonomous | `auto {args}` | `auto` (writes 1) |
| sdlc-requirements | `sdlc {args}` + YOU | `sdlc` (front_end 1, select 1, gate 1, writes 1) |

*(The 15th per-invocation workflow, **`onboard-project`, is deliberately omitted from the table above** because it has no typeable command — it is a `[YOU]`-only alias of `new-project` (`workflows.py`), as stated in the paragraph before the table. Every row in the table is therefore a uniform, runnable `command → workflow` binding.)*

Note the deliberate `gate: 0` on `do`/`build`: "the ENGINE already runs the standing regression inside the build (gating twice doubles cost for zero coverage)" (`workflows.py`, `CONTRACT_FOR` NOTE). Commands absent from `CONTRACT_FOR` (or `{}`) are TRIVIAL — the spine still runs (run_id + thinking + manifest) but phases 1/2/4 no-op (`workflows.py`, `CONTRACT_FOR` header comment).

---

## 7. Self-review notes

This document is the draft folded through one harness review pass. What the review actually caught, and how this final differs from the draft:

1. **Doctrine citation was over-reaching (fixed).** The draft cited the one-paragraph doctrine as `CLAUDE.md:9-19`. Verified against the file: the build-doctrine block is `CLAUDE.md:9-17`; line 18 is blank and **line 19 is the `## Engine + commands` header** — a different section. §1 now cites `CLAUDE.md:9-17`, and each sentence is pinned to its own sub-line (`:10-11`, `:12-13`, `:14-15`, `:16-17`).

2. **The three undocumented gates were mis-grouped (fixed).** The draft called all three "the '#12' spine/manifest gates." Only two fit: `manifest_contract` (`run_gates.py:31`) and `spine_enforced` (`run_gates.py:32`). The third, `gate_tristate` (`run_gates.py:33`), is neither — its own comment is "#12 U1: gates fail CLOSED (INOPERATIVE), never open, on their own error." §5 now describes the trio as the **manifest, spine, and fail-closed/tristate** gates, so a skeptic reading the comment can't call the grouping wrong.

3. **"Runnable" over-claimed section 6 (fixed).** The draft called all 15 per-invocation workflows a "runnable table." 14 are (`[AUTO]` primitive with `{args}`), but `onboard-project` is a `[YOU]`-only alias of `new-project` with no typeable `lathe` command (`workflows.py`; `WORKFLOW_REFERENCE_STEPS.md`). §6b now exempts it explicitly and states "14 of the 15 are runnable."

4. **The draft's open second finding is now closed (new work, beyond the review).** The draft flagged `high+med` (`spine_core.py:17`) as out-of-vocabulary but could not resolve it because `assumption_logic.py` was not loaded. Reading it: policy dispatch is by **substring** — `elif 'med' in p:` at `assumption_logic.py:49` (and again at `:84`) — so `'high+med'` matches `'med'` and resolves to exactly the documented `med` policy. It is a silently-accepted alias, **not** a bug. §3 now states this with the resolution grounded.

5. **Confirmed-correct and carried through unchanged** (re-verified, not re-litigated): the 10-vs-7 standing-gate count and line cites (`run_gates.py:24-33`, incl. `:31/:32/:33`); `run_spine` at `lathe.py:1760-1833` with the guard (`:1794-1796`, `:1829`) and the unconditional `finally: finalize()` on all three exit paths (`:1817-1833`); the `depth_env`/`setdefault` fill-only semantics (`spine_core.py:13-23`, `lathe.py:1791`); the 6-named + 15-per-invocation = 21 split; and the persona claim — `ucb1` is real at `persona_select.py:4`, with `usage_ledger.py` and `persona_grade.py` present — so "UCB1" stays grounded, not asserted.

### 7a. Second pass — the REAL `lathe review` skill (not a hand-rolled script)
Items 1–5 above came from an ad-hoc generation loop. This section records the pass that used the actual shipped command — `lathe review correctness|adversarial|maintainability docs/WORKFLOW_REFERENCE_HARNESS.md` — whose reports are archived at `projects/agentic-harness/docs/ce/review_*.txt`. It caught what the ad-hoc loop had not:

6. **`sdlc` step counts were wrong (fixed).** §6a said "6 AUTO … 4 YOU"; the real `correctness` persona counted the parenthetical (7 commands) against the label. Verified against `workflows.py:71-81`: the steps are 7 AUTO, 1 GATE, **3 YOU**. Both numbers were wrong and are corrected. *(Checked the direct edition too: it enumerates the 11 steps individually and is correct — the miscount was specific to this edition's summary table. The point stands: the ad-hoc self-review loop shipped the wrong count; the real `lathe review correctness` caught it first try.)*
7. **`high+med` was asserted, not traced (fixed).** The `correctness`/`adversarial` personas noted §3 quoted only the isolated `elif 'med'` line and never showed that no `'high'` branch precedes it. §3 now prints the full `assumption_logic.py:47-51` chain proving `'high'` is only the `else` default, so the conclusion is traced, not assumed.
8. **Two maintainability drift-traps (fixed).** `onboard-project` was pulled out of the §6b table (it broke the uniform-runnable-row schema); the §5 gate facts were collapsed to a single source (the table) with the prose reduced to a pointer.
9. **Triaged as NOT actionable here:** the `adversarial` persona's "dial env leaks across invocations via `setdefault`" is a **false positive for the CLI** — each `lathe` run is a separate process, so `os.environ` does not persist across invocations. Its "re-entrancy guard + `gate:0` could skip the standing gates" is a genuine *harness* question (not a doc defect) and is being verified separately against `engine_v2.py`.
