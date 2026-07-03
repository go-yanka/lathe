# Lathe — Gate Stress-Test Report (build-time rigor gates)

*Independent adversarial stress-test of the seven build-time gates that decide what ships (plus STRICT
composition and the acceptance floor's helpers). Every result below was produced by **executing probes
against the real pinned gate functions** — not by reading the code. Probe scripts:
`scratchpad/gate_stress*.py`. Scope this round: the build-time rigor gates (per the maintainer's
"rigor gates first"); the seven standing tree gates are a planned second round.*

## Method

For each gate I imported its decision function from `projects/agentic-harness/tools/` and drove it with:
boundary values, malformed/typed-wrong inputs, **bypass attempts** (craft an input that *should* be refused
but passes), and fail-open probes (does an unrecognized value block or wave through?). A gate is graded:

- **HOLDS** — behaved correctly on every probe.
- **HOLDS \*** — correct, but with a documented bounded limitation (not a defect).
- **FAIL-OPEN** — an input that should be refused was waved through (a real bypass).
- **DEFENSIVE GAP** — a fail-open exists in the function but the engine's call site currently prevents it;
  worth hardening, not live.

## Scoreboard

| Gate | Grade | Note |
|---|---|---|
| Acceptance floor (sandbox) | HOLDS | nonce-framed; covered in earlier sandbox review |
| Traceability / RTM (`rtm_gaps`, `strict_plan_gaps`) | HOLDS | flags orphans; requires CRITERIA under STRICT |
| Regression-proof (`proof_gate`) | DEFENSIVE GAP | `old_passes_all is True` identity check fails open on truthy-non-`True` |
| Spec-lint (`lint_function`) | HOLDS \* | catches tautology/type-only/empty; bounded 8-stub set is the known limit |
| Mutation-score (`mutation_gate`/`equivalent_over_samples`) | FAIL-OPEN | **already filed as issue #2** (fixed-sample equivalence oracle) |
| Test-ack (`ack_ok`/`tests_digest`) | HOLDS | re-arms on edited tests; opt-in default correct |
| Test-kind (`detect_kinds`) | **FAIL-OPEN** | comment-substring false-positive **and** false-negative |
| Gate-the-glue (`count_glue_lines`/`glue_gap`) | **FAIL-OPEN** | line-packing bypass **and** token-INTEGRATION bypass |
| Assumption gate (`parse_assumptions`/`unconfirmed_blockers`) | **FAIL-OPEN** | untagged materiality defaults to `med`, invisible under default `high` scrutiny |
| STRICT composition (`strict_defaults`) | HOLDS | fills exactly 7; empty string = unset (gets filled) |

**Bottom line:** of the gates hammered this round, **three fail open** (test-kind, gate-the-glue, assumption)
plus mutation (already issue #2), and one has a defensive gap (regression-proof). The four that held
(traceability, spec-lint, test-ack, STRICT) held cleanly. Consistent with the earlier pattern: **every gate
subjected to real adversarial input has yielded at least one hole** — which is the argument for finishing the
job on the standing gates too.

---

## Findings (with executed repros)

### F1 — Gate-the-glue: line-packing bypass  · FAIL-OPEN
`count_glue_lines` counts newline-delimited, non-comment lines. Statements joined with `;` on one physical
line count as **one** line, so arbitrary glue slips under the `LATHE_GLUE_MAX` threshold (default 2):

```
glue = "a=1; b=2; c=3; d=4; e=5; f=6; g=7; h=8; import os; os.system('id')"
count_glue_lines(glue)                 -> 1          # ten statements, incl. a shell-out
glue_gap("1", 1, has_integration=False, threshold=2)
   -> [False, 'glue is trivial - not gated']         # REFUSAL EXPECTED, got a pass
```
Impact: the gate's purpose — force an INTEGRATION test on substantial hand-written wiring — is evaded by
formatting. **Fix:** count *statements* (AST nodes), not physical lines.

### F2 — Gate-the-glue: token-INTEGRATION bypass  · FAIL-OPEN
`has_integration` is `bool(getattr(plan, "INTEGRATION", "").strip())` (`engine_v2.py:961`). **Any** non-empty
INTEGRATION string satisfies the gate — including one that asserts nothing (`INTEGRATION = "pass"` or a lone
comment):
```
glue_gap("1", glue_lines=50, has_integration=True, threshold=2)
   -> [False, 'glue exercised by INTEGRATION']        # 50 lines of glue, "exercised" by `pass`
```
Impact: substantial glue is declared "exercised" by a block that runs no assertion. **Fix:** require the
INTEGRATION block to contain at least one `assert` (or actually run and pass), not merely be non-empty.

### F3 — Test-kind: comment false-positive / trigger false-negative  · FAIL-OPEN
`detect_kinds` classifies tests by substring. Both directions break:
```
detect_kinds(["assert f(2)==2  # never raises"])      -> {'example','error'}   # FALSE POSITIVE (comment)
kind_gaps("1", ["error"], detect_kinds(["assert f(1)==1  # error"]))  -> []    # required 'error' satisfied by a comment
detect_kinds(["assert f([1,2,3]) == sorted([3,2,1])"]) -> {'example'}          # FALSE NEGATIVE: a real property/roundtrip test not recognized
```
Impact (both ways): a required *kind* is marked present by a word in a comment (no real test), **and** a
genuine property test is wrongly reported missing — so the gate both waves through weak suites and refuses
good ones. **Fix:** classify by AST/structure (calls, comprehensions, `pytest.raises`, `hypothesis`
decorators), ignoring comments; or require an explicit per-test `kind` tag rather than inferring.

### F4 — Assumption gate: untagged materiality defaults to `med` (invisible by default)  · FAIL-OPEN
`parse_assumptions` maps materiality: `startswith('h')|'crit'`→`high`, `startswith('l')`→`low`, **everything
else (incl. empty/ambiguous)** → `med`. The default policy is `LATHE_ASSUMPTION_POLICY=high`, which blocks
only on `high`. So an assumption the auditor failed to rank explicitly high is silently non-blocking:
```
# ledger entry the auditor emits with an untagged/ambiguous materiality  -> normalized to 'med'
unconfirmed_blockers([{"text":"round half-up?","materiality":"med"}], [], "high")  -> []   # does NOT block
```
Impact: the headline "won't guess silently" guarantee has a quiet default — a material-but-unlabeled
assumption escapes under the shipped default scrutiny. **Fix:** default unknown/ambiguous materiality to
`high` (fail-closed: when unsure, block), not `med`.

### F5 — Assumption blockers: non-canonical materiality escapes  · DEFENSIVE GAP
`unconfirmed_blockers`/`blocking_assumptions` compare materiality against the exact set `{high,med,low}`. A
ledger entry carrying `"medium"` or `"critical"` is treated as **non-blocking even at policy `all`**:
```
unconfirmed_blockers([{"text":"x","materiality":"medium"}], [], "all")   -> []   # escaped entirely
unconfirmed_blockers([{"text":"x","materiality":"critical"}], [], "all") -> []
```
Not currently reachable through `parse_assumptions` (which normalizes to the canonical three), so it's a
defensive gap — but it pairs with F4: **both argue for fail-closed materiality handling** end to end.

### F6 — Regression-proof: identity check fails open on truthy-non-`True`  · DEFENSIVE GAP
`proof_gate` blocks only when `old_passes_all is True` (identity). A caller passing a truthy non-`True`
value slips through:
```
proof_gate("1", "def f(): ...", old_passes_all=1)     -> [False, 'proof present ...']   # NOT refused
proof_gate("1", "def f(): ...", old_passes_all="yes") -> [False, 'proof present ...']
```
The engine's call site passes a real `bool(...)`, so it's not live today. **Fix:** use `if old_passes_all:`
(truthiness), so a future caller can't accidentally disarm it.

---

## What held (and why that matters)

- **Spec-lint** correctly blocked a tautology (`f(5)==f(5)`), a type-only test, and an empty suite (all 8
  trivial stubs survived → refused). Its bounded limit — a fixed 8-stub set can't catch a suite that's weak
  but non-constant — is real and already documented; not a new defect.
- **Test-ack** re-armed correctly when a test string changed (digest mismatch → not acked). Note the digest
  covers `name`+`tests`, not the `prompt`/spec — by design, since the tests are the acceptance oracle.
- **Traceability / RTM** flagged an orphan `FR` with no `TS`, and STRICT correctly refuses a FUNCTIONS plan
  with no `CRITERIA`.
- **STRICT composition** fills exactly the seven toggles and — contrary to a note in an earlier draft of
  `GATES_REFERENCE.md` (now corrected) — treats an **empty string as unset** (`current != ''`), so it *does*
  get filled. The real opt-out is a non-empty disabling value, e.g. `LATHE_STRICT=1 LATHE_TEST_ACK=0`.

## Disposition

- Filed to the maintainer: F1+F2 (glue), F3 (test-kind), F4 (assumption default; F5 folded in as the
  fail-closed hardening). Mutation is already **issue #2**.
- F6 noted as a low-priority hardening (not live).
- `GATES_REFERENCE.md` corrected for the empty-string claim.
- **Next round:** the seven standing tree gates (`stale`, `resource-dups`, `registry`, `pristine`, `lint`,
  `docs-drift`, `env-drift`) with crafted dirty-tree fixtures — pending your go-ahead.

*Reproduce: `python3 scratchpad/gate_stress.py` and `gate_stress2.py` from the repo root.*
