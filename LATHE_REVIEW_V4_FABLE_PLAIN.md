# Lathe — independent strategic review (plain Fable, no harness)

> Produced by Claude Fable 5 reviewing the project **directly** — no harness, no persona injection, no
> decider, no gate. The counterpart to `LATHE_REVIEW_V3_FABLE.md` (same model, run *through* the harness).
> Kept verbatim as generated, for the harness-vs-plain comparison in `REVIEW_MODE_COMPARISON.md`.
> Same-model disclosure: reviewer is Fable, as is the harness pass it's compared against — neither is an
> independent oracle.

I've read the architecture, the plan format, the validator, the benchmark, and — importantly — the three prior review rounds already sitting in the tree (`LATHE_REVIEW_FINDINGS.md`, `_V2`, `_V3_FABLE`). Those already cover the obvious material (pin-cache-as-dataset, transitive invalidation, the cold-rebuild demo, spec golf), so below I've deliberately gone past them. Where I agree with a prior finding I say so in one line and move on.

---

# Lathe — strategic review (independent, round 8)

## 1. What it is, really

Strip the AI framing and Lathe is **a content-addressed build cache in front of a nondeterministic compiler, with an extensional type system**. The compiler is a local LLM; the "type check" is the test gate; the pin (hash of spec+tests+model) is exactly a Nix derivation hash; the never-hand-edit rule is Bazel's "don't edit bazel-out." That's the honest category: hermetic build systems, not coding assistants.

The closest research ancestor — missing from `PRIOR_ART.md` and worth adding — is **Parsel** (Stanford, 2023): decompose into functions with per-function constraints/tests, have an LLM implement each, accept on test pass. Lathe is essentially productionized Parsel plus Nix-style pinning plus a security spine. Commercial neighbors: Tessl (spec-centric, but ships docs/registry, no hard gate), DSPy (declarative signatures compiled against a metric — same philosophy, applied to prompts instead of code). Nothing I know of combines the hard gate + content-hash pin + never-edit doctrine in one shipping tool. The category is real and currently unoccupied.

One reframe matters: Lathe is not a code *generator* with tests bolted on. It's a **verification and provenance layer that happens to include a generator**. The generator is the replaceable part; the gate, pin ledger, and validator are the asset.

## 2. Genuine strengths (including ones nobody has stated)

The audited ones stand — nonce-authenticated sandbox verdict, closed-rule plan validator, mutation probe, the pin ledger. Prior rounds already claimed "pin cache is a dataset" and "the gate is a private benchmark." Three more that I haven't seen stated anywhere:

- **The weak implementer is a spec linter.** Because failure triggers a spec rewrite (not model escalation), the loop mechanically converges on specs that are unambiguous *to a weak reader*. A frontier implementer would paper over ambiguity with good guessing; the cheap model exposes it. Six months of Lathe use produces a spec corpus that has been adversarially tested for clarity — which is also exactly what makes those specs readable by humans and portable across models. The "no escalation" doctrine, which looks like cost dogma, is actually the mechanism that keeps specs honest. This should be stated as a design thesis, not left implicit.

- **The gates turn the repo into a queryable inventory.** One-canonical-implementation-per-capability + no-dup/no-stale + the ctags repo-map means an agent (or a new hire) can cold-start with a *complete, guaranteed-non-redundant* capability index. Everyone else does "context engineering" as retrieval heuristics; Lathe does it as an enforced tree invariant. That's a strength worth naming: the gates aren't hygiene, they're a context contract.

- **Line-level AI provenance for free.** Every generated line traces to (spec hash, test set, model ID, timestamp). Nobody else can answer "which model wrote this line, under what acceptance criteria" — a question that SBOM/AI-attribution requirements are about to make mandatory in regulated shops. Lathe already has the ledger; it just hasn't called it a compliance artifact.

## 3. Real deficiencies / design-level risks

Prior rounds correctly flagged GLUE-untested, textual cache keys, no transitive invalidation, tests-as-strings. Beyond those:

- **The trust chain grounds out in ungated frontier output.** The analyst writes both the spec *and* the tests, one-shot, unverified. If the analyst misreads the goal, the tests encode the misreading and the gate then *certifies* the wrong behavior with a green badge — the system converts "maybe wrong" into "confidently wrong." The mutation probe checks test *strength*, never test *aim*. The tests are the real source code of this system, and they are the one artifact with no gate. Cheapest fix: surface tests for human ack before first build (they're ten asserts — reviewable in seconds); stronger fix: a second, independent model writes tests from the same goal and the two test sets must agree on the pinned implementation.

- **The repair loop's gradient points toward weaker specs.** On failure the analyst rewrites the spec until the local model passes. Nothing checks that rewrite N still means what the user asked at rewrite 0 — the loop is structurally incentivized to negotiate correctness down to the implementer's ability. Needs an intent anchor: the original goal's tests must remain a subset, or a semantic diff of spec rewrites gets logged and flagged.

- **Determinism is shallower than the pitch.** The pin hashes spec+tests+model but not the interpreter or platform. A pin minted on 3.10 that breaks on 3.13 stays green-by-cache forever. Nix hashes the closure; Lathe hashes the recipe. Add an environment fingerprint to the pin, or at minimum re-verify (cheap, no model call) on first use in a new environment.

- **It's a leaf-function factory, and the tree itself is the tell.** `engine_v2.py` is 929 hand-written lines sitting next to a still-present `engine.py`; there are 62 hand-written tools; the root directory carries five review documents and three overlapping guides. The system that enforces "one canonical implementation, no stale files, fix the spec not the code" is not itself built or governed by that system. That's not hypocrisy — assert-string tests structurally can't express what `engine_v2.py` does (stateful, I/O-heavy, integration-shaped) — but it defines the honest ceiling: **Lathe currently industrializes the easy 20% of code and exempts the hard 80% (glue, state, integration).** The self-hosting ratio ("what fraction of Lathe's own lines went through the gate?") is the single most honest metric the project could publish, and today it would be embarrassing. Track it; make it climb.

- **The economics assume a rig.** "Free local implementer" is true for homelab/GPU-enterprise people and false for everyone else. Without a five-minute no-rig path, the funnel is tiny.

## 4. Genuinely novel uses (not in any prior round)

1. **Polyglot retargeting.** The source of truth is spec+tests, not code — so retarget the implementer: build the same plan corpus to Python *and* Rust *and* TypeScript, each gated in its own sandbox. A plan becomes a language-neutral library definition; "porting" becomes a rebuild flag. No tool on the market treats a codebase as recompilable across languages, and Lathe is one sandbox-runner abstraction away from it.

2. **Decompile-to-spec for legacy code (the adopt flow run in reverse).** Point the analyst at an existing human-written function, have it generate characterization tests until the mutation probe passes, then pin the *existing* code under them. The function is now rebuildable, and you've mechanized Feathers-style legacy rescue. This is the brownfield entry everyone wants, and it needs no new machinery — spec_lint already is the grader.

3. **A capability firewall for untrusted agents.** Run a coding agent whose *only* write path to the repo is the Lathe MCP server: the agent may propose plans, never code. The closed-rule validator + sandbox then make prompt injection structurally unable to write arbitrary code into your tree — worst case, the attacker writes a spec whose tests must pass in a network-less sandbox and whose imports are allowlisted. Nobody has shipped "the agent physically cannot commit unvetted code" as an architecture. This reframes Lathe from productivity tool to security boundary, which is a bigger market.

4. **Reproducible-science artifacts.** Journals and artifact-evaluation committees are drowning in "code available upon request." A paper that ships plans+pins lets a reviewer cold-rebuild the analysis code under the gate on their own machine. Small community, but they *write papers about their tooling* — highest word-of-mouth per user of any niche.

5. **Cheapest-sufficient-model routing.** Since the pin key includes the model, build each function with the cheapest model in a ladder and escalate per-function only on gate failure (this is escalation of the *implementer*, which the doctrine permits — the doctrine forbids escalating to dodge a spec problem). The ledger then tells you, per function class, the minimum viable model — an automatic cost optimizer no one offers.

## 5. What to add (usability, in priority order)

1. **A five-minute no-rig path.** `pipx install lathe && lathe init --implementer haiku` (or any cheap API model). The two-endpoint economics story survives directionally; the funnel grows 50×. Nothing else on this list matters if trying it requires standing up llama-server first.
2. **Fresh-clone-green, enforced by public CI.** Round-1 found the standing gate red on a fresh clone (B2). For a tool whose entire pitch is "the gate never lies," this is existential. A badge that runs `selftest` + `gate` on every commit is the fix and the ad.
3. **Test the tests before first build** — show the analyst's asserts for one-keystroke human ack (see §3, risk 1). Ten seconds of friction buys back the system's biggest epistemic hole.
4. **Environment fingerprint in the pin** (or re-verify on new env). Cheap, closes the shallow-determinism gap.
5. **Property-based tests as a first-class test kind** (`{"hypothesis": "st.text()", "prop": "..."}`). One-line asserts cap the correctness ceiling; Hypothesis raises it more than any other single change, and it makes the mutation probe nearly redundant.
6. **Pin GLUE via module-level hashing gated on INTEGRATION tests** — extend the pin to cover the whole assembled module when an INTEGRATION block exists. Closes the untested-hole finding incrementally and starts the self-hosting ratio climbing.
7. **Root-directory hygiene.** Move the five review docs and the redundant guides into `docs/`; delete or archive `engine.py`. The tree is the product's own testimony — right now it testifies against the doctrine.

## 6. Marketing to skeptical engineers — not yet done

Prior rounds proposed the cold-rebuild demo, "market the refusal," category-naming, and spec golf. All fine. Three campaigns nobody has proposed:

1. **A standing forgery bounty.** The sandbox's whole claim is "a malicious test cannot fake a pass" (nonce-framed verdict, stdout to devnull) and the validator's claim is "a hostile plan cannot execute effects." So put money on it: a permanent public challenge — *forge a verdict or smuggle an effect past the validator, win the bounty, get your name in SECURITY.md*. Security tools earn skeptics' trust by surviving public attack, and every failed attempt is free, credible marketing. Every successful one is a fixed CVE and a blog post. The attack surface *is* the campaign. Cost: a few hundred dollars and a SECURITY.md section.

2. **Proof by artifact: a real PyPI package built 100% through the gate.** Not a demo repo — a genuinely useful utility library where every function's spec+tests sit beside it in the tree, and a nightly public CI job cold-rebuilds it across three local models, publishing first-pass rates to a dashboard. The package is the ad; the dashboard is the reproducible benchmark the v2 review said the project still owes; every `pip install` is distribution. Skeptics don't believe demos; they believe artifacts they can `pip install` and audit.

3. **Ride model-release days as the neutral scoreboard.** Every local-model release (Qwen, Llama, DeepSeek…) is a traffic spike with no credible same-day eval. Because pins key on model, Lathe can publish "new model vs. incumbents on N real gated builds — first-pass rate, tries-per-function" within hours of a release, from a corpus no model has trained on. Do it three release-days in a row and "what does the Lathe index say" becomes a reflex in every local-LLM thread. It's the private-benchmark strength weaponized as a recurring publishing channel rather than an internal tool.

And one thing to *stop* doing: the tree currently ships its own review documents at the root, including rounds that praise it. To a skeptical engineer browsing the repo, self-hosted praise reads as marketing even when it's honest audit. Keep the findings (they're genuinely credible — `BENCHMARK.md` admitting "Lathe loses here, 41s vs 5s" is the most trust-building file in the repo), but move them under `docs/reviews/` and lead with the losses. The project's most unusual asset is that its documentation tells the truth against interest; curate that, don't bury it under sprawl.

## Bottom line

Lathe is a hermetic build system wearing an AI-tool costume, and its durable assets are the gate, the pin ledger, and the validator — not the generator. Its deepest risk is epistemic (ungated tests define truth; the repair loop can negotiate intent downward), its deepest limitation is structural (a leaf-function factory whose own engine can't pass through it), and its clearest path to credibility is self-hosting ratio + fresh-clone-green CI + a bounty on the sandbox. The category — deterministic, provenance-carrying AI builds — is real, unoccupied, and worth naming before someone else does.
