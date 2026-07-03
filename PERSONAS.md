# Personas — the expert market: sources, the decider, ratings, and your controls

Lathe starts every substantial job with **thinking**: a *decider* selects expert personas before any code
is written, and can **fetch** an absent expert on demand ("load the program"). Everything below is shipped
and covered by acceptance tests in `review_tests/`.

## Where personas come from (exact sources)

| Tier | Count | Source | License | How |
|---|---|---|---|---|
| **Vendored reviewers** | 12 | [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | MIT | ship in-repo (`ce_personas/`, see `NOTICE.md`) — correctness, adversarial, security, reliability, performance, maintainability, testing, api-contract, data-integrity, data-migration, project-standards, frontend-races |
| **Fetch-on-demand** | 129 | [wshobson/agents](https://github.com/wshobson/agents) | MIT | cataloged; the body is pulled **only when the decider (or you) needs it**, mirrored to `agents/_fetched/` with a `SOURCE` note + the repo's LICENSE |
| **Cataloged, refused** | 2 | zhsama/claude-sub-agent | NOASSERTION | never auto-fetched — unlicensed sources require manual verification |

The full inventory is `projects/agentic-harness/agents/catalog.json` (143 entries). **Compliance is a hard
gate**: auto-fetch only for MIT/Apache/BSD/ISC/Unlicense/CC0 (`agent_router.license_ok`, fail-closed).
A persona is prompt text — **LLM-independent**: it injects into whatever endpoint you configured.

## Purpose-built workflow personas (not part of the 143-reviewer market)

Two personas are authored by Lathe for specific pipeline stages rather than selected by the decider — they
run at fixed points, not by match score:

| Persona | Runs at | Job |
|---|---|---|
| **`requirements-liaison`** (`ce_personas/requirements-liaison.md`) | `lathe clarify` / step 0 of `sdlc` | *Interrogates the user* for clarity before any design — inputs/outputs/success/constraints/edge/non-goals — offering selectable options with a default. Writes `CLARIFIED_GOAL.md`. Does not design or implement. |
| **`assumption-auditor`** (`ce_personas/assumption-auditor.md`) | `lathe assume` (pre-build gate) + advisory at `clarify` | *Adversarially* re-reads the spec against the goal and emits a materiality-ranked ledger of the choices the goal never specified; the gate blocks the build until the HIGH-materiality ones are confirmed (scrutiny is user-governed). Does not design or implement. |

## Buckets — when to invoke which (organized library)

Every one of the 143 agents is tagged with a **when-to-invoke bucket** (`persona_market.bucket_of`, a
deterministic heuristic over name + capability): `review · security · testing-qa · data-ai · devops-cloud ·
frontend-mobile · language · architecture · docs-content · specialized`. Browse with `lathe agent bucket`
(or `lathe agent bucket security`). Buckets are advisory metadata for orientation — the decider still ranks
by match × rating within/across buckets.

## The CE floor + your default agents

- **CE floor (always on):** the vendored Compound-Engineering reviewers are the strongest personas, so the
  decider **guarantees at least one in every selection** — `review auto` always runs correctness +
  adversarial (both CE); the planner floors `correctness-reviewer` even for a non-CE goal. This is not
  configurable-off — it's a governance rule.
- **Your default agents:** `personas.mandatory` in `lathe.config.json` — one or two names injected into
  **every** review/planning call (vendored lens names like `testing`, or catalog personas fetched
  license-gated). The shipped config also **boosts the CE reviewers' priority** by default.

## How the decider decides (the exact pipeline)

For a goal/need `N`, every catalog entry is scored, then reweighted, then ranked:

1. **Match** — `expand_words` overlap (synonym canon + stemming: "authentication bug" reaches the
   security persona; deterministic, no LLM) between `N` and the entry's *capability*, **plus** the same
   overlap against the entry's *name* counted again — a specialist's name is signal
   (kubernetes → the k8s specialists, not a generic container match).
2. **Ratings** (measured performance) — the score is multiplied by `0.5 + rating/10` if the persona has
   been rated (see below); unrated personas are neutral (×1.0) — never punished for being new.
3. **Your overrides** (config) — `personas.priority` multiplies scores per name (your thumb on the
   scale); `personas.mandatory` personas are injected on **every** invocation regardless of match.
4. **Rank** — descending, ties by catalog order; the top-k win. Non-vendored winners are **fetched**
   (license-gated) and their full **body** is injected — as an `@<path>` review lens, or into the
   planner's prompt.

So: of two personas covering the same ground, **the better-measured one wins**; a user preference beats
both; a mandatory persona always shows up; and an unlicensed persona never does.

## Ratings — the empirical layer

```
lathe agent rate "backend api design microservices"   # probe + judge the matched personas
lathe agent ratings                                    # the standings
```

`rate` gives each matched persona a field-relevant probe task ("the 3 most critical, concrete checks
for..."); an independent judge scores the answer 0–10 for specificity/actionability; ratings persist to
`agents/ratings.json` (per-user runtime data, gitignored) and feed step 2 above automatically.

## Your controls (lathe.config.json)

```json
"personas": {
  "priority":  { "security-reviewer": 2.0 },
  "mandatory": [ "testing" ]
}
```

- `priority` — name → weight multiplier on the decider's score.
- `mandatory` — always-injected personas: vendored lens names (e.g. `testing`) or catalog personas
  (fetched license-gated, even off-domain).

## Where the decider fires

- `lathe review auto <files>` — picks review lenses for the code's domain + auto-fetches absent experts.
- `lathe do` / the planner — injects expert lenses (and fetched persona bodies) into spec authoring.
- `lathe agent "<need>" [--spawn]` — the manual surface; `refill` pre-mirrors everything permissive.

Acceptance tests: `test_d7_autospawn` (fetch+inject), `test_persona_overrides` (config steering),
`test_persona_ratings` (empirical reweighting) — all in `review_tests/`, offline, GitHub mocked.
