# Lathe infographic value-brief — coverage vs. actual capabilities (for harness critique)

Purpose: assess whether the current infographic set captures Lathe's CORE differentiating value, or is
superficial. This brief is deliberately run through `lathe review auto` for an adversarial critique before
new graphics are made.

## Current graphics (what they say)
1. `01_build_loop.png` — the pipeline: requirements → analyst writes spec+tests → local model writes code →
   gate → pin; FAIL loops back to sharpen the spec.
2. `02_division_of_labor.png` — analyst (frontier) thinks, implementer (local, model-agnostic) builds.
3. `03_strengths.png` — TEST-GATED · PINNED · NO HAND-EDITS · LOCAL OR ANY MODEL · PROVENANCE.
4. `04_determinism.png` — same spec → same code via pin+reuse, not deterministic generation.

## Strengths the current set UNDER-SELLS or MISSES (claimed core value)
A. **Three ways to run it** (usage modes), from the architecture's DRIVERS + integrations:
   - Standalone in its own shell — the `lathe` CLI / `lathe chat`.
   - Inside an agent you already use — the MCP server (`lathe_mcp.py`) → Claude Code / Cursor / Copilot get
     gate+pin+provenance inside the host agent; plus a Claude skill + plugin.
   - Programmatic / embedded — import the engine; or driven by a prior/driving agent (any shell-running agent).
   - (Both roles are pluggable: analyst = Claude proxy / any OpenAI-compatible / a human; implementer =
     Ollama / llama.cpp / vLLM / local / Claude.)
   - NOTE: the owner referenced a third-party integration "Hermes" that does not appear anywhere in the repo;
     unverifiable — must be confirmed, not invented.
B. **Repo-map for cheap context** (`lathe map`, ctags): give an LLM the code STRUCTURE (names, kinds,
   signatures, scopes) instead of dumping full files → far fewer tokens, fewer tool calls. A real
   token-efficiency lever, entirely absent from the graphics.
C. **Pristine-tree discipline so models don't get confused** — the six standing gates enforce: no
   stale/backup/duplicate files, ONE canonical live implementation per capability (registry + `lathe whatis`),
   no corrupt files, no real-bug lint, docs can't drift. Plus `lathe clean` (quarantine relics) and
   `lathe checkin` (gated: refuses to commit/push with relics, failing gates, or behind upstream). VALUE: an
   AI agent editing the tree is never misled about which version/copy is canonical — the "N copies, which is
   real?" failure mode is structurally prevented. Absent from the graphics.
D. **The feedback loops between the two harnesses** — implementation harness (engine/gates/sandbox) feeds
   results BACK to the thinking harness (analyst): a failing test + banked failed attempt (`_fn_fails/`) →
   the analyst sharpens the spec (repair loop, never escalate); and the CE review gate feeds persona findings
   back into the owning plan for regeneration. This closed loop — "agentic loops" — is arguably the core
   intellectual strength and is shown only as a single thin FAIL arrow today.

E. **The harness runs in multiple MODES, not just "build"** — named, transparent workflows (`lathe flow`),
   each with an up-front contract (when / entry / deliverable / definition-of-done) and a fail-loud
   PASS/BLOCKED verdict:
   - `code-review` — multi-lens review of a change; land only verified fixes (upstream, in the plan).
   - `bug-fix` — reproduce → diagnose from the run log → fix the SPEC → verify → review → release.
   - `enhancement` — scope → build through the harness → integrate → review → document → release.
   - `doc-review` — coherence/accuracy review + docs-drift gate.
   - `new-project` — vendor Lathe → configure endpoints → verify → first gated build.
   VALUE: the same harness reviews, fixes bugs, and enhances — all under the same gate/pin discipline. Absent
   from the graphics.
> **TESTED FINDING (persona auto-fetch scenario, `review_tests/test_persona_fetch.py`, 6/6):** the
> fetch-and-create *mechanism* works — a decider can pick a NON-vendored persona, the license gate allows a
> permissive one, and `_spawn_one` pulls the body, decodes it, stores it + its LICENSE + attribution, and
> instantiates it; it refuses NOASSERTION and is fail-closed when the source is unreachable (network was
> mocked because api.github.com returns 403 in this sandbox). **BUT no decider AUTO-triggers this:**
> `review auto` selects vendored lenses only; the planner injects a non-vendored expert's *name+capability*
> as a hint but does **not** fetch/create it; the only real fetch-create is the user-invoked
> `lathe agent --spawn`. So "decider needs a missing persona → auto-pulls the code → creates it" is
> **mechanism-present but not auto-wired** — a graphic must say "run `lathe agent`", not "the decider does it
> automatically", until that wiring is confirmed/added.

F. **A review-persona library (multi-lens) + on-demand persona decider** — vendored Compound-Engineering
   reviewer personas (correctness, adversarial, security, data, reliability, performance, api,
   maintainability, testing, ui); `lathe review auto` fires a decider that picks the personas applicable to
   the code's domain and injects each as a real reviewer lens. Plus an on-demand catalog of expert personas
   fetched under a permissive-license gate. VALUE: "the right experts think about the right code,
   automatically." Under-shown (only implied).

## Proposed new / revised graphics
5. "Three ways to run Lathe" — standalone shell · inside your agent (MCP) · embedded/programmatic; pluggable
   analyst + implementer.
6. "Cheap context: read the map, not the files" — repo-map/ctags → structure → fewer tokens.
7. "A tree an AI can't get lost in" — pristine gates: no relics, no dupes, one canonical per capability,
   gated check-in.
8. "The loop that learns" — implementation harness ↔ thinking harness: failure banked → spec sharpened →
   regenerate; review findings → plan. The compounding feedback loop.
9. "One harness, many jobs" — the workflow modes: build · review · bug-fix · enhance · doc-review ·
   new-project, each contract-driven with a fail-loud verdict.
10. "The right experts, automatically" — the review-persona library + decider: a change auto-summons the
    correctness/security/adversarial/… lenses that fit its domain.

## Question for the reviewer
Is this coverage now complete and accurate for Lathe's real value, or still superficial/misprioritized?
Which of the four proposed additions is highest-leverage, and is any claim above overstated vs. what the
repo actually implements?
