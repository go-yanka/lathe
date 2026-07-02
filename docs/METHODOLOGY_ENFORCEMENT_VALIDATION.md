# Methodology-enforcement: what's real, what to build before we claim it

**The rule this document exists to hold:** we do not market a claim the harness can't back. The positioning
thesis is "Lathe enforces a proven methodology, so the *kind and comprehensiveness* of testing come from the
process, not the model's discretion." Before that goes in a whitepaper, it gets validated against the code.
This is Lathe's own doctrine — nothing ships unproven — applied to Lathe's marketing.

Method: empirical. Security battery (`review_tests/battery_security.py`, 35/35), a direct validator call,
and a source grep across `engine_v2.py` + `tools/` + `qa/`. Verified 2026-07-02 at v2.1.3; the build-spec
status column re-verified against **v2.1.4** and again **v2.1.5** the same day (test-ack gate and the #2
traceability acceptance test both independently reproduced — v2.1.5 in a fresh worktree, 12/12).
Cross-checked by a Fable pressure-test (`GRAPHIC11_FACTCHECK.md` sibling analysis, recorded in the commit).

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

## What is NOT enforced (the comprehensiveness gap — do NOT claim yet)
The thesis says comprehensiveness comes from the methodology. The harness enforces test *existence, passing,
non-triviality* — nothing about *kind or coverage*. Verified absent (grep → 0 source files each):
| Mechanism the claim needs | Present? |
|---|---|
| Mutation-*score* threshold (kill ≥X% of mutants) — real mutation testing, not the single stub probe | ❌ 0 files |
| Requirement/acceptance-criterion → test traceability, enforced | ❌ 0 files |
| Property-based tests as a required kind | ❌ 0 files |
| Independent oracle (tests authored/approved without seeing the impl) | ⚠️ PARTIAL as of v2.1.4 — a **test-ack gate** (`LATHE_TEST_ACK=1`, `lathe ack`, `tools/test_ack.py`) now forces a human to read/approve a plan's test set before build, and any rewrite (incl. the repair loop) re-forces it. Opt-in, default off. Verified present + wired in `engine_v2.py:90`. It's a *human re-read*, not yet a second independent model author — but it closes the "tests slip through unread" hole. |
| Regression test that must FAIL on pre-fix code (bug-fix) | ❌ 0 files |
| Glue / end-to-end coverage of each capability's entry point | ❌ (glue largely ungated) |

Workflow contracts (`bug-fix`, etc.) state done-criteria in **prose**; the steps are advisory (`lint-spec`,
a `[you]` "fix the spec" step). Nothing gates on the contract. So kind and comprehensiveness are **100% at
the analyst's one-shot discretion today.**

**The sentence a skeptic falsifies in one line:** *the tests are authored one-shot by the same model that
writes the code, and nothing checks them against the requirement.*

## The claim, honestly scoped for right now
CAN say: "Lathe won't ship a *function* that isn't proven by passing, non-trivial tests — enforced, no
override." CANNOT say (yet): "comprehensiveness/kind of testing is dictated by the methodology" or "cannot
produce *anything* without testing" (glue is ungated → say *function*, not *anything*).

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

1. ❌ **Regression-test-must-fail-on-old-code (bug-fix).** *Open — unchanged by v2.1.4.* Highest leverage,
   cheapest, fully structural.
   Build: in the bug-fix path, run the new test against the *pre-fix* implementation; require it to FAIL,
   then pass post-fix. Acceptance test: a scratch plan where the new assert passes on old code is REFUSED.
   Claim it unlocks: "a bug fix is not accepted unless it comes with a test that reproduces the bug."
2. ✅ **Requirement→test traceability, enforced.** *DONE+ACCEPTED in v2.1.5 — independently reproduced here
   (`test_traceability.py` 12/12).* Plans may declare `CRITERIA = [{'id','text','tests': ['fn'|'fn:idx']}]`;
   the closed-rule AST-literal validator **refuses** an unmapped criterion, a dangling fn ref, an
   out-of-range test index, or a duplicate id — and criteria-free plans stay valid (opt-in, backward
   compatible). `lathe trace <plan>` emits the criterion→test→**pin→model** matrix (verified: real pin hash,
   model column, coverage summary on a live gated build). Claim now marketable, honestly scoped: "every
   **declared** acceptance criterion is covered by a named test, by construction" — *declared*, because
   nothing forces a plan to declare criteria yet (that's the gap between this and full comprehensiveness).
   This is also the compliance artifact — §6.1 of strategy.
3. ❌ **Real mutation-score threshold.** *Open — v2.1.4 still ships only the single-stub `spec_lint` probe,
   not a scored mutation pass.* Build: generate mutants of the accepted impl; require the suite to
   kill ≥X%. Acceptance test: a suite that passes but kills <X% of mutants BLOCKS the build. Claim:
   "test comprehensiveness is measured and gated, not assumed." This is the one that most directly earns the
   word "comprehensiveness."
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

**Scorecard for the maintainer LLM (as of v2.1.5):** **1/6 done** (#2 traceability), **1/6 partial**
(#4 oracle, via test-ack), 4/6 open. The full comprehensiveness claim still cannot ship — it hinges on
**#3 mutation-score**, which is the mechanism that actually earns the word "comprehensiveness," and #1.
Next-in-line by leverage: **#1 regression-must-fail-on-old-code** (cheapest, fully structural), then
**#3 mutation-score threshold**. Marketing may now add the *declared-criterion traceability* claim (#2 is
verified) but stays off "comprehensiveness" until #1 and #3 land their acceptance tests green.

## Go-forward gate (the reflexive rule)
- Ship the **floor** claim now (it's verified above).
- For the **comprehensiveness** claim: implement 1–3 first (they convert "methodology-defined" from branding
  to fact), land their acceptance tests green in CI, and only then update the whitepaper/marketing to claim
  it. 4–6 harden it into a moat.
- Until then, the whitepaper and kit stay on the *enforcement floor* wording (already corrected in
  `WHITEPAPER_DRAFT.md` §3 and `MARKETING_SALES_KIT.md`). No doc claims comprehensiveness the harness
  doesn't gate.
