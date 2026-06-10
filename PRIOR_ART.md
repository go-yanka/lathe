# Prior art — an honest map

Lathe was built independently, with no reference to any of the tools or papers below. This map was
produced *afterward*, to place the work honestly in context. The short version: **every individual idea
here is prior art.** What appears unoccupied is the specific combination and three deliberate choices.

We adopt the field's existing vocabulary rather than coin new terms.

## Each pillar is established prior art

| Lathe pillar | Existing name / closest work |
|---|---|
| Spec + tests as source of truth, code regenerated | **Spec-driven development** — GitHub Spec Kit, AWS Kiro, Tessl, BMAD-METHOD |
| Only accept code that passes tests | **TDD-for-LLMs** (Mathews & Nagappan, arXiv:2402.13521); **eval-driven development** (arXiv:2411.13768) |
| Learn from failed attempts | **Reflexion** (arXiv:2303.11366) and related self-improvement loops |
| Cheap model executes, premium model plans | Cost cascades — **FrugalGPT** (arXiv:2305.05176), **COPE** (arXiv:2506.11578) |
| A small local model generates code | Common — **Aider**, **Cline**, **Sourcegraph Cody** all support local Ollama models |

We do **not** claim to have invented any of these, and we do **not** claim "local-first" as a
differentiator — the assistants above disprove it.

## What appears unoccupied (the combination + three contrarian choices)

Checked feature-by-feature against the tools' own docs/repos where reachable. **Verified absent** = read
the docs/repo, the feature is not there. **Not found** = could not confirm either way.

| Marker | Status across tools examined |
|---|---|
| **No fall-through** — a failed generation forces a *spec fix*, never escalation to a bigger model | Unmatched. Every cascade examined (FrugalGPT, COPE) escalates; the tools that auto-handle failure (Aider, GoCodeo) *auto-fix*, they do not force spec revision. |
| **Content-hash pinning** — accepted output cached by `hash(spec+tests+model)` for byte-stable rebuilds | **Verified absent in every tool read.** None pin accepted output for reproducible regeneration. This is the rarest piece. |
| **Behavioral UI gating** — generated UI must pass a live-browser functional test to ship | Not found as a built-in accept/reject gate in the tools examined. |

No tool examined had **3 or more** of Lathe's markers together; the combination — no-escalation +
content-hash pinning + behavioral gating — was unoccupied across the verified set. (Local-first is *not*
counted as a differentiator; several assistants have it.)

## Two more candidates (flagged, not yet verified)

Two design choices feel distinctive but have **not** had a feature-by-feature verification pass, so we flag
them as candidates, not claims:

- **Per-function specs + tests as the atomic unit of generation** — vs. feature/PRD-level spec tools and
  task-level TDD. It's the granularity that makes a small model reliable and the pins fine-grained.
- **A bug fix forced to be a design revision** — because code is never hand-edited, every correction must go
  back to the plan, so *thinking-change precedes implementation-change* and determinism survives
  maintenance. (The seed exists in model-driven engineering; the *forcing-function* framing is what we
  haven't seen stated.)

Both deserve the same verification we gave the markers above before they are printed as "novel."

**Honest caveats.** "Unoccupied" is verified only for tools read in primary sources (AWS Kiro, GitHub Spec
Kit, Tessl, OpenSpec, Aider, Cline, Cody, BMAD, squad-kit, Augment). A few (e.g. Cursor's failure
handling, Genval) remain **unverified** — treat them as unknown, not absent. Absence of evidence over a
finite survey is not proof of global non-existence.

## Why the choices are right (not just different)

The contrarian choices line up with what the literature names as the binding constraints:

- Reproducibility of AI-generated code is unsolved — only ~68% runs out-of-the-box (arXiv:2512.22387). →
  *pinning.*
- Self-repair is bottlenecked by **feedback quality, not model size** (Olausson, arXiv:2306.09896; Pan,
  arXiv:2308.03188). → *failure-as-asset loop.*
- Small models can't reliably self-correct even with correct feedback (arXiv:2308.03188, 2404.17140). →
  *no fall-through; fix the spec, don't trust the model to fix itself.*
- Reliably filtering incorrect outputs is a named open problem (arXiv:2310.03533). → *behavioral gating +
  pinned rebuilds.*

## What we explicitly do not claim

- That any individual idea is novel. It isn't.
- That "local-first" is a differentiator. It isn't.
- Any cost-savings figure. The study that would support one does not, on inspection.

## On independent invention

Arriving at this independently is a signal that the design is *convergent* — multiple people reaching the
same structure is evidence it's sound, not derivative. But for the purpose of novelty, prior art is prior
art regardless of whether we'd seen it. The honest framing, used throughout this project, is: *developed
independently; here is precisely how it relates to X, Y, Z.*
