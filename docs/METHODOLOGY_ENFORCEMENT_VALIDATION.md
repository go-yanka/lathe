# Methodology-enforcement: what's real, what to build before we claim it

**The rule this document exists to hold:** we do not market a claim the harness can't back. The positioning
thesis is "Lathe enforces a proven methodology, so the *kind and comprehensiveness* of testing come from the
process, not the model's discretion." Before that goes in a whitepaper, it gets validated against the code.
This is Lathe's own doctrine — nothing ships unproven — applied to Lathe's marketing.

Method: empirical. Security battery (`review_tests/battery_security.py`, 35/35), a direct validator call,
and a source grep across `engine_v2.py` + `tools/` + `qa/`. Verified 2026-07-02 at v2.1.3; the build-spec
status column re-verified against **v2.1.4** → **v2.2.0** the same day (test-ack; #2 traceability 12/12;
#1 regression-proof 8/8 + 6/6; v2.1.7 strict/SDLC umbrella 7/7 + 8/8; **#3 mutation-score 9/9 + 17/17 pure
logic incl. every fail-closed case**; SDLC RTM gate all-pass — all independently reproduced in fresh
worktrees). Cross-checked by a Fable pressure-test (`GRAPHIC11_FACTCHECK.md` sibling analysis, recorded in
the commit).

## What IS enforced today (the floor — verified, claimable now)
| Mechanism | Enforced? | Evidence |
|---|---|---|
| A unit must have ≥1 test | ✅ structural | validator rejects empty `tests`: "every FUNCTION needs a non-empty tests list" (verified directly) |
| Code must pass its tests in isolation | ✅ structural, no override | sandbox nonce-verdict; battery 35/35; the gate is outside the model's action space |
| Tests must be non-trivial | ✅ | mutation probe (`spec_lint`) rejects tests a stub can pass |
| One canonical impl per capability; no stale/dupe files | ✅ | six standing gates fail the build |
| No hand-editing generated code; pinned, reproducible | ✅ | provenance markers + content-hash pins |

**This much is true and differentiated vs. "an agent that runs tests."** The line: an agent treats testing
as *policy it can skip*; Lathe makes passing tests a *precondition on the artifact* the model can't override.
That claim is honest today.

## The comprehensiveness gap — mostly CLOSED as of v2.2.0 (was "do NOT claim yet" at v2.1.3)
When this doc was first written (v2.1.3), the harness enforced test *existence, passing, non-triviality* and
**nothing** about kind or coverage — every row below was ❌ (grep → 0 source files). Over v2.1.4→v2.2.0 the
maintainer built and I independently reproduced four of the six. Current state:
| Mechanism the claim needs | Present? |
|---|---|
| Mutation-*score* threshold (kill ≥X% of mutants) — real mutation testing, not the single stub probe | ✅ **v2.2.0** (`tools/mutation_score.py`, `LATHE_MUTATION_SCORE=<0..1>`; reproduced 9/9 + 17/17 pure logic, fail-closed) |
| Requirement/acceptance-criterion → test traceability, enforced | ✅ **v2.1.5** (`CRITERIA` + validator + `lathe trace`; reproduced 12/12) |
| Regression test that must FAIL on pre-fix code (bug-fix + enhancement) | ✅ **v2.1.6** (`LATHE_REGRESSION_PROOF`, generalized to all changes under STRICT v2.1.7; reproduced 8/8 + 6/6) |
| Independent oracle (tests authored/approved without seeing the impl) | ⚠️ PARTIAL as of v2.1.4 — a **test-ack gate** (`LATHE_TEST_ACK=1`, `lathe ack`, `tools/test_ack.py`) forces a human to read/approve a plan's test set before build, and any rewrite (incl. the repair loop) re-forces it. Opt-in, default off. Verified wired in `engine_v2.py:90`. It's a *human re-read*, not yet a second independent model author — but it closes the "tests slip through unread" hole. |
| Property-based / required *kind* of test per contract | ❌ still open (#5) |
| Glue / end-to-end coverage of each capability's entry point | ❌ still open (#6) — glue largely ungated |

The composition of these is forced together by **STRICT mode** (`LATHE_STRICT=1`, v2.1.7): under it, all
development runs through traceability + test-ack + regression-proof + mutation-probe, no picking and
choosing. So kind and comprehensiveness are **no longer at the analyst's one-shot discretion** for the two
still-open axes: what remains discretionary is the *kind* of test (property vs example) and whether *glue*
is exercised — everything else is now gated.

**What a skeptic can still falsify (and only this):** the tests are authored one-shot by the same model
that writes the code (mitigated, not eliminated, by test-ack #4-partial and by mutation-score forcing the
suite to actually discriminate); and *glue* code past the leaf-function core is not coverage-gated (#6).

## The claim, honestly scoped for right now (v2.2.0)
CAN say (all verified): "Lathe won't ship a *function* that isn't proven by passing, non-trivial tests —
enforced, no override"; "test **comprehensiveness is measured and gated** — a suite that can't kill the
accepted code's mutants doesn't pin" (#3); "every **declared** acceptance criterion is covered by a named
test, by construction" (#2); "a change ships no fix without a test that reproduces the bug" (#1); and under
STRICT, "the SDLC process is enforced by the build, not left to discipline" — for the gates that exist.
CANNOT say (still): "your **whole system** is comprehensively tested" (comprehensiveness is measured
per-gated-function under a bounded mutation-operator set, not whole-program — #5 kind-of-test and #6 glue
coverage remain open); "cannot produce *anything* without testing" (glue is ungated → say *function*, not
*anything*); and don't imply the tests have a fully independent author yet (#4 is a human-ack, not a second
model).

## Build spec — make the full claim true, each with its own acceptance test
Ordered by leverage. **A mechanism is not "done" — and its claim is not marketable — until its acceptance
test passes.** Add each acceptance test to `review_tests/` so the claim can't silently regress.

**Status legend:** ❌ open · ⚠️ partial · ✅ done+accepted. Per-mechanism status added 2026-07-02
after independently verifying v2.1.4 on the rebased branch (D7 auto-fetch, D5a/D5b analyst guards, D8
synonyms, and the test-ack gate all PASS locally). **Updated for v2.1.5** the same day: mechanism #2
(traceability) landed and was **independently reproduced** here — `review_tests/test_traceability.py`
**12/12** against the v2.1.5 validator, including step 4's real gated build + the pin→model matrix (I stood
up a local implementer stub; enforcement steps 1–3 are endpoint-independent). Transitive-pin invalidation
and the ornith-9b benchmark, previously maintainer-reported, are now maintainer-reproduced on their machine
(I remain sandbox-blocked on `api.github.com`, so those two stay *maintainer-verified, not reviewer-run*).

1. ✅ **Regression-test-must-fail-on-old-code (bug-fix).** *DONE+ACCEPTED in v2.1.6 — independently
   reproduced here (`test_regression_proof.py` 8/8 + the pure gate logic 6/6).* Opt-in
   (`LATHE_REGRESSION_PROOF=1`): on a **changed** function the engine extracts the old accepted impl from
   the built module and runs the *new* tests against it in the same sandbox as the gate; if every new test
   passes on the old code, the change ships no reproducing test and is **REFUSED before a single generation
   token is spent** (verified: `tok_total == 0` on the refusal path). New functions and unchanged pins are
   exempt; default off. Decision + extraction are pure/harness-built (`tools/regression_proof.py`,
   `engine_v2.py:529`). Claim now marketable: "a bug fix is not accepted unless it comes with a test that
   reproduces the bug."
2. ✅ **Requirement→test traceability, enforced.** *DONE+ACCEPTED in v2.1.5 — independently reproduced here
   (`test_traceability.py` 12/12).* Plans may declare `CRITERIA = [{'id','text','tests': ['fn'|'fn:idx']}]`;
   the closed-rule AST-literal validator **refuses** an unmapped criterion, a dangling fn ref, an
   out-of-range test index, or a duplicate id — and criteria-free plans stay valid (opt-in, backward
   compatible). `lathe trace <plan>` emits the criterion→test→**pin→model** matrix (verified: real pin hash,
   model column, coverage summary on a live gated build). Claim now marketable, honestly scoped: "every
   **declared** acceptance criterion is covered by a named test, by construction" — *declared*, because
   nothing forces a plan to declare criteria yet (that's the gap between this and full comprehensiveness).
   This is also the compliance artifact — §6.1 of strategy.
3. ✅ **Real mutation-score threshold.** *DONE+ACCEPTED in v2.2.0 — independently reproduced here
   (`test_mutation_score.py` 9/9 + 17/17 on the pure logic).* `LATHE_MUTATION_SCORE=<0..1>`: before accepted
   code may pin, the engine generates deterministic AST mutants (arithmetic/comparison/integer-constant
   operators) and runs them through the same `validate()` as the gate; if the suite kills fewer than the
   threshold fraction, the build is **BLOCKED** and the weak-tests reason is banked to `_fn_fails`. Verified:
   the classic weak suite (`square(2)==4`, which the `x+x` mutant also satisfies) is refused; adding
   `square(3)==9` makes it green. **Hardened to fail CLOSED** — malformed gate inputs (`killed > total`,
   negative, bool) REFUSE rather than wave through (the harness's own self-review caught it failing open;
   I reproduced all four fail-closed cases). Claim now marketable, scoped: "test comprehensiveness is
   *measured and gated* — a suite that can't distinguish the code from its mutants doesn't pin." This is the
   mechanism that earns the word "comprehensiveness" — *scoped to the gated function's test adequacy under a
   bounded, deterministic operator set*; it is not whole-program coverage (see #5, #6).
   **✅ v2.2.0 boundary defects (LATHE_REVIEW_V2.md §16) — FIXED in v2.2.1, reproduced here.** E2 (equivalent
   mutants falsely blocking correct code) is closed by a deterministic differential probe (`mutation_equiv.py`)
   that excludes provably-equivalent survivors from the denominator — my exact `scale` repro now builds GREEN,
   while a genuinely weak suite still blocks. E1 (silent fail-open on no-mutants) is closed by broadened
   operators plus a loud `unmeasurable` warning + `mutation_unmeasured` ledger flag. **The scoped-
   comprehensiveness copy is now CLEAR TO SHIP**, and the maintainer added the exact scoping clause the claim
   needs — mutation score is *"a bounded tripwire for vacuous tests (small operator set, capped per function,
   equivalent mutants excluded), not exhaustive mutation coverage."* Keep that clause wherever the claim
   appears; without it "measured comprehensiveness" over-reads.
4. ⚠️ **Independent oracle.** *PARTIAL as of v2.1.4.* The **test-ack gate** (`LATHE_TEST_ACK=1`, `lathe ack`,
   `tools/test_ack.py`, wired at `engine_v2.py:90`) now forces a human to read/approve a plan's test set
   before build, and re-forces it on any rewrite (incl. the repair loop). Verified present + wired locally.
   Still short of the full claim: it's an opt-in (default-off) *human re-read*, not a second independent
   model that authors/approves tests without seeing the impl. Remaining build: a second analyst instance
   sees only the spec/contract and writes-or-approves the tests. Acceptance test: the impl-authoring model
   cannot also be the sole test author for a gated unit. Claim (full): "the code is checked against tests it
   didn't get to write." Claim (marketable now): "no gated plan builds until its tests are read and
   acknowledged — the repair loop can't slip a rewrite past that gate."
5. ❌ **Kind-of-test per contract.** *Open — unchanged by v2.1.4.* Build: enhancement ⇒ property tests for
   each declared invariant; code-review ⇒ adversarial cases. Validator enforces the required kind per
   workflow. Acceptance test: an enhancement plan with no property test for a declared invariant is refused.
6. ❌ **Gate the glue.** *Open — glue remains ungated in v2.1.4; keep saying "function", not "anything".*
   Build: require each capability's public entry point to be exercised by ≥1 end-to-end
   test; until then, drop "anything" from all copy. Acceptance test: a module whose GLUE entry point has no
   integration test is flagged.

**Scorecard for the maintainer LLM (as of v2.2.0):** **3/6 done** (#1 regression-proof, #2 traceability,
#3 mutation-score), **1/6 partial** (#4 oracle, via test-ack), **2/6 open** (#5 kind-of-test, #6
gate-the-glue). All three done mechanisms independently reproduced here (#3: 9/9 acceptance + 17/17 pure
logic incl. every fail-closed case). **The "comprehensiveness" claim is now UNLOCKED — scoped.** Marketing
may say *test comprehensiveness is measured and gated (mutation-score), every declared criterion is covered
by a named test, and a change ships no fix without a reproducing test* — all verified. The remaining honest
qualifier: comprehensiveness is measured **per gated function's test adequacy**, not whole-program — #5
(required kind of test per contract) and #6 (glue/entry-point coverage) are still open, so keep saying
*"the code Lathe gates is comprehensively tested"* not *"your whole system is."*

### Strict / SDLC mode — the composition layer (v2.1.7, independently reproduced)
`LATHE_STRICT=1` composes the enforcement stack into a single SDLC umbrella rather than adding a new
mechanism (so the **scorecard count is unchanged**). Under it, *all* development — new code and
enhancements alike — is forced through: mandatory `CRITERIA` (#2), forced test-ack (#4-partial), the
mutation-probe stub-block (`LATHE_LINT_SPEC=block`) on new code, and — the notable generalization —
**regression-proof (#1) applied to every *changed* function, not just bug fixes**. An explicitly-set env
var still wins over the umbrella; default off = zero behavior change. Policy is pure + pinned
(`tools/strict_mode.py`), wired at `engine_v2.py:86`.
Reproduced here: `review_tests/test_strict_mode.py` **7/7** on a real gated build (prompt-aware local
implementer stub) plus **8/8** on the pure policy logic directly. The load-bearing case verified: under
strict, a **no-proof *enhancement* is REFUSED** (regression-proof is no longer bug-fix-only), the three
refusal paths (no-CRITERIA / un-acked / stub-satisfiable) are model-free, and flag-off is a no-op. This
lets a team claim, honestly: *"following the SDLC process is enforced by the build, not left to
discipline"* — for the mechanisms that are actually built. **As of v2.2.0 strict also composes #3** —
`strict_defaults` now adds `LATHE_MUTATION_SCORE=0.5` alongside test-ack/regression-proof/lint-block
(verified in `tools/strict_mode.py`). So STRICT now forces #1 + #2 + #3 + #4-partial together. It still
does not reach *whole-program* comprehensiveness (#5 kind-of-test and #6 glue-coverage are outside the
composition), so the SDLC claim covers the gated leaf-function core, not glue/entry-points.

## Go-forward gate (the reflexive rule)
- The **floor** claim: verified since v2.1.3, ship freely.
- The **comprehensiveness** claim: mechanisms 1–3 are **built, reproduced, and CI-gated** (v2.1.5/2.1.6/2.2.0),
  and the v2.2.0 boundary defects (E1/E2) are **fixed and reproduced (v2.2.1)** — so the whitepaper/marketing
  are now **CLEAR** to make the scoped comprehensiveness claim — *test comprehensiveness is measured and gated
  (mutation-score); every declared criterion maps to a named test; a change ships no fix without a reproducing
  test* — provided the copy keeps **both** scope clauses: **(a)** per gated function, not whole-program; and
  **(b)** the maintainer's tripwire clause — *"a bounded tripwire for vacuous tests (small operator set, capped
  per function, equivalent mutants excluded), not exhaustive mutation coverage."*
- The remaining honest limits to preserve in copy: #4 is a human-ack (not a second independent test-author),
  #5 (required kind of test) and #6 (glue/entry-point coverage) are open. So: never "your whole system is
  comprehensively tested"; always "the code Lathe gates is." Keep "function", not "anything," for glue.
- **Action item for the docs:** `WHITEPAPER_DRAFT.md` §3 and `MARKETING_SALES_KIT.md` were written to the
  *enforcement-floor* ceiling and can now be upgraded to the scoped-comprehensiveness wording above — but that
  edit should itself be reviewed against this gate before publishing (don't let "measured comprehensiveness"
  silently become "complete coverage").
