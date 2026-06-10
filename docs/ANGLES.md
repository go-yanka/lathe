# Positioning angles — pick the lead per audience

This project has many sharp angles. Don't force one "spine." Pick the **lead** for each audience/artifact
and let the rest be supporting facets. This file is the menu, so it doesn't get lost.

## The headline outcome

**Deterministic code.** AI that writes the same *correct* code every time, and stays that way for life.
Everything else is the *how* that makes this believable.

## The distinctive idea (the one we think is genuinely fresh)

**A bug fix is a forced design revision.** You can't patch the code (it's a build output), so every fix
has to go back to the plan — which *forces the design to be re-evaluated before anything is corrected.*
**Implementation never changes unless the thinking changes first.** Consequence: **determinism survives
maintenance** — fixes flow *through* the design, not around it, so the system never drifts.
*(Relates to model-driven engineering; the forced-design-revision behavior is the fresh framing — verify
before printing "new.")*

## The angle menu (each is nearly a headline)

**Pain / anti-decay** — for anyone who's felt it
- "Your AI coding sessions rot as they age. This one gets *sharper* as it ages."
- "Stop chatting with the AI and hoping. Build with it."

**Determinism / trust**
- "AI that writes the same correct code every time."
- "The model's confidence gets no vote. Nothing ships unless it passes its tests."
- "Your source of truth is the intent, not the code — the code is a throwaway build output."

**Maintenance / the fresh one**
- "You can't patch the code. So every bug fix is a design decision."
- "Thinking-change before implementation-change. Always. By construction."

**Engineering discipline (SDLC)**
- "An AI-native SDLC: keep the process, swap the labor."
- "Lockfiles, test gates, reproducible builds — for AI codegen."

**Economics / access / privacy** (strong, esp. for regulated industries — our demo is pharma)
- "Frontier-grade discipline on a $200 used gaming GPU."
- "Spend the expensive model on thinking; let a cheap local model do the typing."
- "Your code and data never leave your machine."

**Mechanism / 'magic sauce'**
- "The whole trick is one file: a design and a test, per function."
- "When the AI fails, you don't buy a bigger model — you sharpen the spec."
- "Failures aren't retries. They're assets that make the next build better."

**Credibility**
- "Built independently — and the research independently says it's the right architecture."

## Angle → audience → artifact

| Lead with… | Hooks… | Best in… |
|---|---|---|
| Anti-decay / anti-vibe-coding | builders, indie devs | X thread, HN post |
| Determinism + the bug-fix idea | senior engineers, skeptics | dev blog, the white paper |
| SDLC discipline | eng leaders, architects | LinkedIn, an enterprise one-pager |
| Cheap + private + local | startups, hospitals, regulated industries | a focused pitch / one-pager |
| The research agrees | researchers, the doubtful | a short research-flavored note |

## The rule
One core (the white paper + `HOW_IT_WORKS.md`), many front doors. Write the core once; change only the
*lead* per audience. Never rewrite the substance to chase a headline.
