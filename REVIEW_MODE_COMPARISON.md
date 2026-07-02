# Same model, two modes: harness-persona review vs. plain review

An experiment. The same reviewer model (Claude Fable 5) reviewed Lathe two ways:

- **Harness mode** (`LATHE_REVIEW_V3_FABLE.md` + its `lathe review auto` pass): Fable ran the harness's
  vendored review personas — the decider picked correctness, adversarial, and api — each injected as a lens,
  output forced into severity + `file:line` + concrete-failing-input + fix.
- **Plain mode** (`LATHE_REVIEW_V4_FABLE_PLAIN.md`): Fable reviewed the project directly. No personas, no
  decider, no gate, no output schema. One open prompt: "what is this, strengths, deficiencies, novel uses,
  what to add, how to market."

One honest caveat before the verdict: the two runs had **different targets**. The harness pass was auditing
*my V3 draft document*; the plain pass was reviewing *the project*. So this isn't a clean apples-to-apples on
the same input — it's a comparison of what each *mode* is good at. And both are Fable reviewing work in
Fable's own family, so neither is an independent oracle.

## What each mode actually produced

**Harness mode caught contradictions.** Reviewing my V3 draft, the personas found cross-section logical
breaks I'd missed: the `rm -rf` demo contradicting §2a/§3 (pins contain the code; GLUE is unpinned), the
fine-tuning flywheel being reward-hackable, the drift sentinel that can't work because verification makes no
model call, the semantic-key fix that would *worsen* the stale-green bug. Every finding was a "if you follow
this advice, here's the input where it fails," with a line number. Several were genuinely CRITICAL/HIGH and
materially fixed the document.

**Plain mode produced insight.** Reviewing the project, Fable-plain generated framings nobody — not me, not
the personas, not three prior rounds — had reached: "the weak implementer is a spec linter" (no-escalation
as a clarity mechanism, not cost dogma); "leaf-function factory" + the **self-hosting ratio** as the single
most honest metric the project could publish; the trust chain grounding out in *ungated frontier-written
tests*; the repair loop's gradient pointing toward weaker specs; determinism hashing the recipe but not the
closure (Nix comparison); **Parsel** and **DSPy** as the missing prior art; and novel uses — polyglot
retargeting, decompile-to-spec, a capability firewall for untrusted agents, cheapest-sufficient-model
routing — plus a forgery-bounty marketing campaign.

## Which is better

**Neither — they're good at different jobs, and the split is the interesting result:**

| | Harness-persona mode | Plain mode |
|---|---|---|
| Best at | **verifying a concrete artifact** — contradictions, "this advice fails on input X", correctness | **generating insight** — new framings, prior art, novel uses, strategy |
| Output | disciplined: severity + file:line + failing input + fix | ranged, prioritized by originality |
| Failure mode | narrow — the code-review lenses (correctness/adversarial/api) are the *wrong* tools for "how should we market this" | unstructured — no severity, no line cites, easy to hand-wave |
| Forcing function | the persona + severity + line-cite schema *forces* rigor | none — quality rides entirely on the model |
| On this task | sharpened and de-bugged a specific document | reframed the whole project |

For **auditing a deliverable** (a doc, a plan, a diff) where there's a right answer and contradictions to
catch, harness mode won: the structure is a forcing function, and the adversarial persona in particular found
breaks a free-form read glides past. For **open-ended strategy and creativity**, plain mode won decisively:
the harness's lenses are code-review lenses, the decider can only pick from them, and none of them is a
"strategy" or "novelty" lens — so the scaffolding actively constrained the generative task.

## The insight that matters

**This A/B is a data point about Lathe's own thesis.** Lathe's whole claim is that a harness of gates makes a
*verifier*, not a thinker — it doesn't make the underlying model smarter, it makes its output checkable. The
experiment shows exactly that, one level up: the harness made Fable a better **critic** (structure caught
contradictions), and made it a worse **strategist** (structure constrained ideation). The harness adds value
where there's something to verify against; it subtracts value where the job is to think.

Which points at the right workflow, and it's Lathe's own two-tier split applied to reviews:

> **Think in plain mode; verify in harness mode.** Generate strategy/ideas with the unconstrained model,
> then run the resulting artifact back through the harness personas to catch where the ideas contradict
> themselves. That's exactly what happened here by accident: plain-Fable's ideas (round 8) are the raw
> material; the harness personas (round 7) are what caught that my write-up of similar ideas had logic holes.
> Neither alone is the answer.

Two corollaries:
- **Model choice dominated harness choice for insight.** Fable-plain out-originated the Opus-persona passes
  of prior rounds by a wide margin. For the *thinking* half, upgrade the model, not the scaffolding.
- **"Run everything through the harness" is wrong** — the instinct this project (and this reviewer) keeps
  reaching for. The harness is for the half of the work that has a right answer. Forcing strategy through
  code-review personas produces confident, well-formatted mediocrity.

## Recommendation
Use harness-persona review for concrete artifacts with correctness stakes (code, plans, specs, a finished
doc). Use plain strong-model review for strategy, positioning, and ideation. Chain them: plain generates,
harness verifies. And when picking where to invest — the model is the lever for insight; the harness is the
lever for trust.
