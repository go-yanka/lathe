# Prior Art & Credits

An honest map of the ideas Lathe stands on. Lathe is its own code (MIT), but several of its patterns are
inspired by published work. We credit inspirations even when we share no code, and we carry the upstream
NOTICE + attribution wherever we actually reuse code.

## Patterns Lathe is inspired by

- **Google Agent Development Kit (ADK) — long-running agent patterns.**
  Source: `github.com/GoogleCloudPlatform/generative-ai/tree/main/agents/adk/new-hire-onboarding` (Apache-2.0).
  Blog: "Build long-running AI agents that pause, resume, and never lose context with ADK."
  We take the **architectural patterns, not the code** (ADK is a Gemini/Google framework; Lathe is a
  standalone Python harness — no ADK code is copied, so no Apache-2.0 code obligation attaches; this is an
  inspiration credit). The patterns and how Lathe relates:
  - *Durable state machine over chat history* — Lathe already embodies this: the kanban **board**
    (`harness.db`, SQLite) is the explicit, persisted state machine; the planner reads board state, never
    replays conversation history.
  - *Checkpoint on every action* — Lathe pins each gated function (content-hash) and git-commits each green
    build; progress is durable, restart-survivable.
  - *Event-driven pause / resume-on-signal (dormancy gates)* — the one pattern Lathe does **not** yet fully
    have (it is cycle/poll-driven). Adopting it would let a long job go dormant awaiting an external signal
    (human approval, a slow dependency, a time window) and resume cleanly from board state. Tracked as a
    candidate capability for workflow-style autonomy.
  - *Multi-agent delegation* — Lathe uses a deliberate two-tier split (Claude analyst ↔ local implementer)
    rather than a sub-agent graph; the delegation idea lives more in a prior agent (the driving agent) than in Lathe.

- **Compound Engineering (`EveryInc/compound-engineering-plugin`, MIT).** Lathe's multi-lens review
  discipline (`lathe review`) and the `simplify-code`/`pattern-recognition` reviewer ideas draw on CE.

- **The "plans are data, the engine runs them" lineage** — make/pip/setup.py: a plan is a build script;
  Lathe treats it as such and hardens accordingly (see `SECURITY.md`).

## Where we reuse actual code
None currently. If upstream code is ever vendored, its LICENSE + NOTICE are included here and beside the file.
