# Lathe — Persona Selector Stress-Test Report

> **✅ RESOLVED (PR #13 / issue #9).** The 99/143-unreachable finding below drove the persona redesign, which
> shipped a UCB1 explore/exploit selector + usage ledger. Re-verified: **143/143 personas reachable** over
> time (UCB1 pulls every unvisited arm), so the dead tail is gone. As of **v2.16.0 the selector is ON by
> default** (`LATHE_PERSONA_UCB` defaults on; `0`/`false` opts out). The findings below are retained as the
> record of what was found and how the fix was validated — not as open defects. **Caveat (capstone v2.16.0):**
> the *live review-lens decider* (`lathe.py`) still calls the old word-match, and the work-based grade
> pipeline is not yet wired, so UCB1 currently runs explore-by-count only — see the capstone report.

*Adversarial stress-test of the persona **decider** (`agent_router.select_agents_for_goal` / `score_match`),
executed against the real 143-persona `catalog.json` — not reasoned about. Probe script:
`scratchpad/persona_stress.py`. This is the empirical backing for the redesign in
`PERSONA_SYSTEM_DESIGN.md` / issue #9.*

## Method

The selector matches a goal to personas by **word overlap**: it stems both sides and counts shared tokens
(with a small synonym table). I drove it with (P1) known-domain goals to see if the right expert surfaces,
(P2) the same need in different words, (P3) a broad sweep to measure how many of the 143 are reachable at
all, (P4) degenerate input, and (P5) the name-as-signal path.

## Scoreboard

| Probe | Result |
|---|---|
| P1 right expert surfaces? | **NO (mostly)** — wrong personas rank at or above the right one |
| P2 wording sensitivity | **FRAGILE** — rephrasing the same need returns unrelated personas |
| P3 catalog reachability | **99 of 143 never surface** across a full-taxonomy sweep (69% dead weight) |
| P4 degenerate input | empty goal → empty selection (no fallback) |
| P5 name-as-signal | works only if you already know the persona's name |

**Bottom line:** the selector is meaning-blind. It picks by literal token overlap, so it (a) frequently
ranks the wrong expert first, (b) collapses when the same need is worded differently, and (c) leaves more
than two-thirds of the library permanently unreachable. This is the same failure mode filed against the
test-kind gate (issue #5), and it empirically confirms the "personas that will never be used, ever" concern.

---

## Findings

### PS1 — the right expert often doesn't surface  · WRONG-PICK
Known-domain goals, top-3 returned:
```
"fix a SQL injection in the login query"        -> security-reviewer, backend-security-coder, review      (ok)
"async worker has a race condition deadlocking" -> julik-FRONTEND-races-reviewer, reliability, csharp-pro (a frontend-races reviewer + C# for a backend async bug)
"kubernetes pod keeps OOMing on deploy"         -> DATA-MIGRATION-reviewer, c4-container, deployment-engineer (top pick is data-migration; the devops expert is 3rd)
"React component re-renders and leaks memory"   -> frontend-developer, C-PRO, c4-component               (C-language expert for a React leak)
"REST endpoint returns 500 on empty body"       -> adversarial-reviewer, security-reviewer, api-contract-reviewer (the api specialist is 3rd)
```
Irrelevant specialists (`c-pro` for React, `data-migration` for k8s, `csharp-pro` for async) rank high purely
on incidental token overlap; the domain-right persona is frequently not the top pick.

### PS2 — rephrase the need, get garbage  · FRAGILE
Three phrasings of one auth/security need:
```
"authentication bypass"   -> adversarial-reviewer, security-reviewer, backend-security-coder   (good — 'auth' synonym hit)
"a login credential leak" -> adversarial-reviewer, security-reviewer, backend-security-coder   (good — 'login'->auth)
"sign-in token forgery"   -> design-system-architect, receipt-verifier, ui-ux-designer         (WRONG — no synonym word present)
```
The moment the goal avoids the hard-coded synonym words (`auth/login/credential`), the security experts
vanish and unrelated UI personas surface. Selection quality depends on the user's vocabulary, not the
problem.

### PS3 — 99 of 143 personas are unreachable  · DEAD WEIGHT (the headline)
Firing a broad sweep of 13 goals covering the entire bucket taxonomy (security, db, perf, testing, frontend,
api, concurrency, devops, docs, errors, ML/data, architecture, auth) and taking the top-5 for each:
```
personas that EVER surface: 44 / 143
personas that NEVER surface: 99 / 143
never-surfacing sample: ai-engineer, arm-cortex-expert, bash-pro, blockchain-developer, cloud-architect,
                        conductor-validator, customer-support, data-engineer, database-optimizer,
                        dx-optimizer, elixir-pro, ...
```
**More than two-thirds of the paid-for library can never be selected**, even when you deliberately probe
their domain. They are shipped, licensed, catalogued — and dead. This is exactly the "there to be there, not
used" problem.

### PS4 — no fallback on a vague goal  · GAP
```
select_agents_for_goal("please help me", …) -> []      # nothing selected
```
A goal with no domain keywords selects **no** persona (the correctness+adversarial floor still runs, but no
specialist is brought in — and there's no "when unsure, ask / pick a generalist" path).

### PS5 — name-as-signal only helps if you know the names  · LIMITED
```
goal mentions "rust-pro" -> rust-pro ranks first
```
Naming a persona explicitly works — but that requires the user to already know the 143-name catalog, which
defeats the point of an auto-selector.

---

## What this means for the redesign (issue #9)

Every gap here is answered by the proposed design:

- **PS1/PS2 (wrong picks, wording-fragile)** → replace/augment word-overlap with a **semantic match**, and
  let **earned grades** (not just match) drive ranking so a proven expert isn't out-ranked by an incidental
  token hit.
- **PS3 (99 dead personas)** → the **usage ledger + explore/exploit**: surface the never-used tail, give it a
  chance to earn a grade, and prune what stays useless. Today nothing even *measures* this — the number
  above had to be computed by an external probe.
- **PS4 (no fallback)** → the **verbal mode** ("for this vague goal I'd bring in a generalist / here are my
  best guesses — pick one") turns an empty result into a conversation.
- **PS5 (name-only)** → `lathe agent bucket` helps discovery, but grade-driven auto-selection is what removes
  the need to know names.

*Reproduce: `python3 scratchpad/persona_stress.py` from the repo root.*
