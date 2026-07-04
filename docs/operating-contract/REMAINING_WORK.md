# Lathe — Final Punch List (close-out of the independent review)

*The consolidated list of everything still open after the review→fix→verify→document cycle. Ordered,
with acceptance criteria, so the implementer can finish it and we wrap up. Standing rules unchanged:
**build harness-buildable modules through the harness** (spec+tests → regenerate; trunk hand-edits called
out), and **every invocation emits its manifest** (the evaluation instrument). All verified-done items are
elsewhere; this file is only what's left.*

Status at close-out: `main` @ **v2.14.0**. Everything below is either a rollout decision, an unfinished
enhancement, or a behavioral check that needs a live model. No known defects remain.

---

## 1. Flip persona explore/exploit ON by default  · rollout decision  · issue #9
**State:** shipped and verified (UCB1 selector + usage ledger + grades, PR #13), but `persona_orchestrator.
is_enabled()` defaults **OFF** (`LATHE_PERSONA_UCB=1` / `personas.explore_exploit=true` to enable). So the
99/143-unreachable fix — and the usage-ledger/grade **recording** on the review path (`record_run`) — only
happen when a user opts in. Out of the box, the old word-match path still runs.
**Validation already provided:** simulated UCB1 reaches **143/143** personas over time (issue #9 comment).
**Do:** make explore/exploit the default (unconditionally, or default-on under STRICT / `LATHE_THINK≥medium`,
your call). Keep the graceful-degrade fallback for a missing ledger.
**Acceptance:** with no env set, the live decider selects via UCB1; the tail becomes reachable; `record_run`
writes `agents/usage_ledger.jsonl` on a normal `review`/`do`. The persona docs (`PERSONA_SYSTEM_DESIGN.md`)
lose the "opt-in until validated" caveat.

## 2. Property-based adversarial synthesis  · unfinished enhancement  · issue #11
**State:** the adversarial-synth **gate** shipped (v2.13.0, `adv_synth.py`); `needs_adversarial` correctly
triggers on gate/validator plans. But it **admits example cases** (`admit_cases`) rather than **generating**
them — there is no property-based / Hypothesis-style generation, so a coverage gap the analyst didn't think
of still isn't produced internally. This is the half that makes the harness catch its *own* gaps.
**Do:** add generative adversarial-case synthesis for decision/gate plans — boundary encodings, comment/
whitespace tricks, packed statements, mislabeled inputs, fail-open probes — and require the suite to kill
them before the module pins. Consider folding the same generator into the mutation-equivalence oracle (#2),
which is still a fixed ~34-sample check.
**Acceptance:** a deliberately-weak gate plan (tests that pass a known bypass, e.g. the `;`-packed glue or
`# error`-comment classes) **cannot pin** under STRICT — the synthesized cases kill it — with **no external
reviewer** involved. Runs through the harness.

## 3. Mutation-equivalence: move off fixed samples  · minor  · issue #2
**State:** the acute #2 defects are fixed (raise-vs-return counts, `==` primary oracle, fails toward
not-equivalent). It remains a fixed ~34-probe oracle.
**Do:** (couples to #2 above) replace the fixed probe set with seeded property-based sampling; keep the
fail-closed direction.
**Acceptance:** a mutant that differs only outside the old fixed probes is no longer wrongly excluded.

## 4. Formally close the umbrella  · housekeeping  · issue #12
**State:** every phase shipped and was independently re-probed — Phase 0 (manifest), Phase 1 (spine), 2a
(19 workflows + promotion + U2 clamp), 2b + **U1 gates-fail-closed** (`run_gates.py` no longer prints
"regression clean" on a missing gate; `tristate_gate.py` added). The `hreview` free-text sub-finding is moot
(file removed; review now emits a per-run manifest).
**Do:** confirm nothing lingers and **close #12**. (Items 1–3 are tracked on #9/#11/#2, not #12.)

## 5. Behavioral acceptance — run once against a live model  · verification the reviewer can't do headless
The reviewer verified everything structurally + via each feature's own gate, but this container has **no
metered model endpoint**, so three end-to-end behaviors were never driven with a real model. Run these once
on a rig with an analyst + local implementer and attach the manifests:
- **T4 analyst tokens fire:** a `do` that makes ≥1 analyst call → manifest `usage.tokens.by_role.analyst.total
  > 0`, `source:"measured"`, `completeness.all_calls_attributed:true`.
- **Adv-synth actually blocks:** the weak-gate plan from item 2 is refused live.
- **Full workflow e2e:** a real `build` and a real `review auto` each emit a complete manifest with populated
  `selection.personas` (+`why`), `contributors[]` with verbatim findings, gate verdicts, and cost.
**Acceptance:** the three manifests are attached to #12 (or a `docs/ce/` sample) as the final proof.

---

### Disposition
Items 1, 4, 5 are near-term/small (a default flip, a close, a rig run). Items 2, 3 are the real remaining
engineering (generative synthesis). Once these land, the operating contract and the persona system are
complete end to end and the review engagement closes. The reviewer will verify each as it ships (executable
probes / manifest checks), then confirm final close.
