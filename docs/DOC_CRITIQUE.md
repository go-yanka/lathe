# Documentation critique

*Fable's review of Lathe's documentation as a body of work — structure, honesty, redundancy, and whether a
newcomer or a skeptic can actually get in. Separate from the code audit. Measured against the repo at
`94e75df`.*

## The headline
The docs are **unusually honest and unusually sprawling.** Honesty is the project's single best asset —
`BENCHMARK.md` literally says "Lathe does NOT win here" (41s vs 5s), and the whole review history sits in
the tree including findings against the project. That is rare and worth protecting. But there are **21
markdown files totaling ~3,500 lines at the repo root**, several overlapping, several carrying internal
residue that a public reader shouldn't see. The problem isn't quality; it's navigation and leakage.

## Finding 1 (HIGH) — internal residue is shipping in public docs
34 occurrences across six files reference things that don't exist in, or shouldn't leak to, the public
repo: **"a prior agent"** (an internal driving-agent name) appears as if the reader knows it;
**`<LATHE_ROOT>`** appears as a literal, unsubstituted placeholder; **`projects/your-product`** is
referenced repeatedly (`LATHE_CAPABILITIES.md` cites it 3×) but **does not exist in the repo**; and
`CLAUDE.md` still carries host-specific notes ("D: drive is OFF-LIMITS", WhatsApp pings). A newcomer hits
these in the first five minutes and concludes the repo is a scrubbed export of something private — which
undercuts the "audit everything" trust pitch.
**Fix:** a scrub pass — define or remove "a prior agent," substitute `<LATHE_ROOT>`, either ship a stub
`projects/your-product` or stop referencing it, move host-specific notes out of shipped `CLAUDE.md`.

## Finding 2 (HIGH) — no single entry point; the reader has to guess
There are at least four docs that all want to be "start here": `README.md`, `LATHE_GUIDE.md`,
`FOR_PROJECTS.md`, `LATHE_CAPABILITIES.md`, plus `ARCHITECTURE.md` and `docs/HOW_IT_WORKS.md`. They
overlap heavily and none says "read these in this order." A skeptic bounces.
**Fix:** README becomes a 60-second pitch + a "quickstart in 5 commands" + an explicit reading path
("new here → HOW_IT_WORKS; evaluating → ARCHITECTURE + SECURITY; using it → LATHE_COMMANDS; the why →
whitepaper"). Everything else moves under `docs/`.

## Finding 3 (HIGH) — the review/strategy docs at root read as self-promotion
Six `LATHE_REVIEW_*` / strategy files now sit at the repo root, including rounds that praise the project.
Even though they're honest audit, self-hosted praise at the root reads as marketing to exactly the
skeptical engineer the project wants. (This was V4's point and it's correct.)
**Fix:** move all review + strategy docs to `docs/reviews/` and `docs/strategy/`; keep them (they're
credible), but lead the repo with the method and the losses, not with reviews of itself.

## Finding 4 (MEDIUM) — status legend is great but inconsistently applied
`LATHE_CAPABILITIES.md` has an excellent ✅/🔌/🧠 legend. But README's "Six standing gates" and other
feature lists drop the status, so a reader can't tell shipped-autonomous from built-but-optional. The
capability map (`docs/CAPABILITY_MAP.md`) fixed this; the older docs haven't caught up.
**Fix:** propagate the status legend to every feature list, or point them all at the capability map.

## Finding 5 (MEDIUM) — version/claim drift across files
The model story was reconciled (12B, model-agnostic) but the docs still carry archaeological layers:
`LATHE_CAPABILITIES.md` §0 talks about "canonical `2026-07-01q`" and a two-tree split that a public user
has no context for; several docs still describe the private-product tree. Dates and "current state"
sections will keep drifting because they're maintained by hand in many places.
**Fix:** one CHANGELOG (exists, good) as the single source of "what's current"; strip point-in-time
"current state" prose from the other docs and link the changelog instead.

## Finding 6 (LOW) — the strongest material is buried
The Cleanroom/V-model framing (now in `PRODUCT_STRATEGY.md`/`WHITEPAPER_DRAFT.md`) and the honest-benchmark
story are the most differentiating things the project has, and they're the hardest to find. The
`decay-vs-build` / `division-of-labor` diagrams in `docs/` are good and underused.
**Fix:** lead with them. The methodology anchor belongs in the README's first screen.

## What NOT to change
- The honesty. Do not sand off "Lathe does NOT win here," the circularity disclosures, or the kept-in
  corrections. That candor is the brand; most projects would kill for it.
- `SECURITY.md`. It's the best-written doc in the repo — states the threat model, the tiers, and the
  irreducible floor plainly. Use it as the template for the others' tone.
- `LATHE_COMMANDS.md` / `FOR_PROJECTS.md` command-with-example format. That's exactly right for reference
  docs; just link them from a clear entry point.

## Priority order
1. Scrub internal residue (Finding 1) — it's a five-minute credibility leak on every read.
2. One entry point + reading path (Finding 2).
3. Move reviews/strategy under `docs/` (Finding 3).
4. Propagate status legend (Finding 4); collapse "current state" prose into the changelog (Finding 5).
5. Surface the methodology framing and the diagrams (Finding 6).

Net: the documentation's *content* is above average and its *honesty* is exceptional; its *information
architecture* is the weak point. It reads like an internal wiki that was made public, not a public project
that was documented. Fixing navigation and leakage — not writing more — is the work.
