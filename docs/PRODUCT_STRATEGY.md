# Lathe — product strategy

Written by the round-7/8 reviewer (Fable), in response to the owner's questions: enhancements to the
development model, positioning, whitepaper, monetization, open-vs-closed, market, push plan, the niche,
and the SDLC/methodology angle. This is strategy, not audit — opinions here are argued, not verified.

---

## 1. The one decision first: do NOT pull it from open source

Closing the source would kill the product. Three reasons, in order of weight:

1. **A verifier must be auditable.** The entire pitch is "don't trust the model, trust the gate." A
   closed-source gate is an oxymoron — you'd be asking people to blindly trust the thing whose job is to
   remove blind trust. Every security-adjacent tool that matters (compilers, TLS, hash functions) won its
   position by being inspectable.
2. **The core is small and the ideas are now public.** The engine plus validator plus sandbox is a few
   thousand lines, and the whitepaper explains the design. Close it, and the open reimplementation becomes
   the standard while you hold a proprietary copy of yesterday's version. Ask HashiCorp how relicensing
   Terraform went; OpenTofu exists.
3. **Distribution is your scarce resource, not IP.** One maintainer, no community yet. Open source is the
   only marketing budget you have.

**The right structure is open-core:** MIT core (engine, gate, pins, validator, CLI, MCP) forever; money
lives in a commercial layer on top (§6). Docker gave away the runtime and monetized the registry. Do that.

## 2. The niche — what this has that nothing on the market has

From five research sweeps plus two Fable reviews, the capabilities nobody else ships:

| Capability | Who else has it |
|---|---|
| Hard test gate as *acceptance* (not a repair loop) | nobody (closest: dormant Micro Agent) |
| Content-hash pinned, byte-identical rebuilds | **nobody** — the acknowledged hole in Tessl's $125M thesis |
| Per-function spec+test granularity | nobody (everyone is feature-level) |
| Requirement → spec → test → code → model **traceability by construction** | **nobody** — and this is the money one |
| Refuse-to-escalate / spec-repair loop | nobody (everyone escalates to a bigger model) |
| One-canonical-per-capability enforced tree | nobody (everyone does retrieval heuristics) |
| Pin ledger as verified training data; gate as private model benchmark | nobody has even noticed this class |
| Enforced, machine-checked SDLC stages | nobody — see §3 |

## 3. The owner's sharpest instinct: methodology, not tool

The market is drowning in tools ("use this, take that") and has abandoned methodology. But **anchor on
disciplines a working developer actually used and trusts (2000–2020), not obscure 1980s methods.** A Fable
fact-check (recorded in `docs/GRAPHIC11_FACTCHECK.md`) killed the original Cleanroom-first framing: nobody
knows Cleanroom, its "developers never test their own code" rule is *false as a general claim*, and TDD/CI/
review/lockfiles didn't "die" — they *erode under pressure*. The corrected, more relatable mapping:

- **Test-first / TDD** (Beck, 2003) → Lathe's analyst writes the tests before the implementer writes code.
- **CI, "never merge red"** (Fowler 2000/2006; Jenkins/Travis) → the gate is a required green build with no
  override.
- **Lockfiles / reproducible builds** (`yarn.lock` 2016, `pip freeze`, Nix content-addressing) → hash-pinning,
  applied to generated code.
- **The compiler contract** (the most relatable, already in the README) → nobody hand-edits a compiler's
  output; if it's wrong, fix the source. Lathe extends that to LLMs: if the code is wrong, fix the spec.
- **The V-model / requirements traceability (DOORS/Polarion)** → the pin ledger traces requirement → spec →
  test → code → model. This one is niche but it's the *paying* niche (§6.1), so keep it for that audience.

The true story is **enforcement, not resurrection**: these practices fail not because people reject them but
because they run on willpower and willpower loses to deadlines (`--no-verify`, rubber-stamped reviews, a red
build merged "just this once"). Lathe moves them onto the machine, where they can't be skipped. *(Cleanroom
and Fagan inspections — the one discipline that genuinely died of human-hour cost — belong in `PRIOR_ART.md`
as cited ancestors, not in the headline.)*

**Positioning statement:** *"Everyone ships tools. Lathe ships enforcement. The practices you already
believe in — test-first, never-merge-red, locked builds, don't-hand-patch-the-compiler — made unskippable by
a machine that can't be talked out of them under deadline."*

Structural move: **separate the method from the tool** (Scrum : Jira :: your-method : Lathe). Name the
methodology (candidates: *Gated Development*, *Enforced TDD*, *Deterministic AI Development*), publish a
short manifesto + a one-page spec of its artifacts (plan, gate, pin, ledger), and let Lathe be the
reference implementation. Methods spread further than tools, and methods are monetizable (§6).

## 4. Enhancements to the development model itself (Fable's list)

> **Status (as of v2.5.1):** this started as a wishlist; most of it has since shipped and is verified in
> `METHODOLOGY_ENFORCEMENT_VALIDATION.md`. Shipped: #1 (test-ack + mutation-score gates), #3 (provenance
> coverage, now in the whitepaper), #6 (property/edge/error enforced by the `LATHE_TEST_KIND` gate, v2.2.4),
> #7 (`lathe trace` traceability matrix). Partially: #2 (assumption gate audits silent intent-drift against
> the spec, v2.5.0 — the immutable-anchor rule itself is not yet a hard gate). Still open: #4 (stage gates as
> a portable method spec), #5 (environment-closure fingerprint in pins). Left in place as the original
> reasoning; read the status line, not the tense.

Beyond the §15 defects and V3/V4 findings, methodology-level upgrades:

1. **Gate the tests.** The system's one ungated artifact is the one that defines truth (V4 finding). Add a
   human-ack step (ten asserts, ten seconds) or dual-author tests (two models, must agree) before first
   build. In methodology terms: independent test authorship — exactly what the V-model prescribed.
2. **Intent anchor across repairs.** The repair loop may negotiate a spec down to what the weak model can
   pass. Rule: original acceptance asserts are immutable across rewrites; a repair may add or clarify,
   never delete. Log a semantic diff of every rewrite.
3. **"Provenance coverage" as a first-class metric.** % of shipped lines that carry spec+test+model+hash
   provenance (Lathe's self-hosting ratio, generalized). Like test coverage was for the 2000s, this can be
   *the* metric of the AI era — and only Lathe can compute it today. Publish the definition; own the number.
4. **Stage gates as data.** The flow contracts (when/entry/deliverable/done) are CMMI-style stage gates
   already; formalize them into the method spec so an org can adopt the process without the tool.
5. **Environment fingerprint in pins** (V4): hash the closure, not just the recipe.
6. **Property-based tests as a test kind** — raises the correctness ceiling more than any single change.
7. **Traceability matrix as an emitted artifact:** `lathe trace` → FR-### → plan → asserts → pin → model,
   as a report. Trivial to build (the ledger has it all) and it is *the* artifact regulated industries pay for.

## 5. The whitepaper — how to rewrite it

Split into two documents:

**A. The manifesto (evergreen, method-level).** Structure:
1. The problem, in the reader's scars: "almost-right" AI code, review burden, slop, irreproducibility
   (68% of AI projects don't run; cite it).
2. The diagnosis: *a conversation is not a build* — keep this, it's the best line the project has.
3. The reframe: the practices you already believe in — test-first, never-merge-red, locked builds, the
   compiler contract — don't fail because they're wrong; they *erode under deadline pressure*. AI made the
   erosion fatal by making bad code cheap to produce. (Cleanroom/Fagan as cited ancestors, not the hook.)
4. The method: the loop, the artifacts (plan/gate/pin/ledger), the principles (never hand-edit, never
   escalate, fix the spec), the metric (provenance coverage).
5. The limits, stated against interest: what it can't do (stateful glue, the granularity ceiling), what's
   unproven (publish the benchmark *inside* the paper with the losses left in — the 41s-vs-5s table is the
   most credible thing the project owns).
6. Call to action: run the cold-rebuild demo.

**B. The technical whitepaper (versioned, tool-level).** Architecture, threat model, pin format spec,
benchmark methodology + raw data, reproduction commands. Engineers trust appendices, not adjectives.

Style rules: engineer voice, no superlatives, every number sourced or omitted, every claim paired with the
command that checks it. The existing paper's honesty ("Lathe does NOT win here") is a brand asset — lead
with it.

## 6. Money — yes, several ways, all open-core-compatible

Ordered by fit and willingness-to-pay:

1. **Compliance & traceability (the real business).** Regulated software (DO-178C avionics, IEC 62304
   medical, ISO 26262 automotive, EU CRA everywhere) pays enormous sums for requirement→test→code
   traceability, and it is precisely why those industries *can't* use Copilot-class tools today. Lathe
   produces the trace by construction. Product: signed AI-BOM/attestation reports, audit exports,
   policy packs ("no code ships without provenance"), long-term-support gate versions. Buyer: QA/compliance
   directors, not developers. This niche is small in logo count and large in contract size — and it has a
   regulatory clock (CRA: 2026–27) pushing buyers toward you.
2. **The registry (the platform play).** The package-manager-of-contracts (V3 §4.1): free public specs,
   paid private registries for teams — exactly npm's model. Plus a team pin cache (Bazel remote-cache
   analog): one engineer's gated-green build is everyone's instant verified build. Both are natural SaaS.
3. **The scoreboard (the audience play).** "Lathe Index": model-release-day evals on a public corpus
   (free, builds the brand) + private procurement evals on the customer's own corpus (paid): "which local
   model should we standardize on" is a purchasing decision with real budget and no current tool.
4. **Certification & training (the Scrum play).** If the method gets a name and traction, courses and
   practitioner certification monetize the *methodology* without touching the MIT core. This is how Scrum
   made money while being an open idea. BMAD-METHOD's ~50k stars prove developers adopt methodology
   frameworks; nobody has monetized one for the AI era yet.
5. **Fine-tuning pipeline (later).** `export-dataset` + hosted fine-tune loop on the customer's verified
   triples: "your local model, trained on your own gated history." Needs the flywheel guards from V3.

Anti-recommendation: don't sell "AI coding assistant" seats. That market is a knife fight between
companies with nine-figure war chests, and Lathe's differentiators are invisible in a seat-based demo.

## 7. Is there a true market? Honest sizing

- **Beachhead (pays):** regulated/safety-critical + air-gapped/defense + provenance-hungry platform teams.
  Small number of buyers, high value, slow sales cycles, near-zero competition because cloud-first
  assistants structurally can't follow you there.
- **Community (doesn't pay, distributes):** local-LLM/homelab crowd, TDD/methodology enthusiasts,
  reproducible-builds people, educators. They make the method legible and produce contributors.
- **Mass developer market:** not yours yet and maybe never — requires the benchmark to be public and the
  onboarding frictionless, and even then the spec-writing tax filters most people out. Be honest about it.
- Evidence demand exists: Spec Kit's 117k stars and Kiro's 100k waitlist prove appetite for *disciplined*
  AI development; the SO trust collapse (~½ of devs distrust AI output) proves appetite for verification.
  Nobody has yet converted that appetite into a *verified* method. That's the open lane.

## 8. Push plan (sequenced)

1. **Credibility floor first** (unchanged from V2 §14): public reproducible benchmark on real local
   hardware; 5-minute no-rig onboarding (`pipx install lathe && lathe init --implementer <any-api-model>`);
   fresh-clone-green CI badge.
2. **Name the method, publish the manifesto** (§3, §5) — the "we automated Cleanroom" essay is the launch post.
3. **The three campaigns from V3/V4:** cold-rebuild demo (honest version) · standing **forgery bounty** on
   the sandbox/validator · a real pip-installable package built 100% through the gate with a public
   nightly dashboard.
4. **Model-release-day scoreboard** as the recurring publishing channel (every Qwen/Llama/DeepSeek drop is
   a free traffic spike with no credible same-day eval).
5. **The compliance paper**: "Mapping deterministic AI builds to DO-178C / IEC 62304 / CRA traceability
   requirements" — boring title, rich buyers. This one document can open the §6.1 market.
6. Move the accumulated review docs to `docs/reviews/` and lead the README with the method + the losses
   (V4's point: self-hosted praise at the repo root reads as marketing; curated honesty is the brand).

## 9. Comparison on the SDLC axis, plainly

| | Conventional SDLC (pre-AI) | Current AI tools | Lathe |
|---|---|---|---|
| Requirements | documents, DOORS | a chat prompt | the plan (versioned, machine-read) |
| Design review | meetings, inspections | none | analyst + persona review gate |
| Implementation | humans | LLM, unverified | LLM, gated |
| Unit test | written after, coverage-tracked | maybe generated, advisory | the *acceptance condition*, written first |
| Integration/acceptance | staged, manual sign-off | none | INTEGRATION / road_ready / flow contracts |
| Traceability | manual matrices, audits | none | by construction (pin ledger) |
| Reproducibility | build systems | none | content-hash pins |
| Discipline enforced by | managers and process | nobody | the machine |

That last row is the pitch. The disciplines in the left column are the ones working engineers already
believe in — test-first, never-merge-red, locked builds, don't-hand-patch-the-compiler; the risk with AI
codegen is that they get *skipped* under deadline, not that they were ever wrong. Lathe makes them
unskippable by moving them into the build. **"The discipline you already believe in — enforced."**
