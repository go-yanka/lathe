# Lathe — a strategic review (round 7, new model)

**Who wrote this:** the same reviewer as `LATHE_REVIEW_V2.md`, now running on a newer, more capable model
(Claude Fable 5). The earlier reviews audited correctness — did the fixes land, do the gates hold. This one
answers a different question: **what is this thing actually, what could it become, and how do you tell people
about it.** The persona critique of this document ran on Fable too (see the appendix for the log proof and
the shim used to route the harness's reviewers to the new model).

Facts and defect claims below inherit from the audited v2 report; nothing here retests them. What's new is
the framing, the ideas, and the marketing. Standard disclosure applies: same model on both sides of every
review pass. Version reviewed: v2.1.3 (`f7a58fc`).

---

## 1. What is this, really? Stop comparing it to Copilot.

Every comparison so far — mine included — put Lathe next to coding assistants: Aider, Cursor, Copilot,
Spec Kit, Kiro, Tessl. That's the wrong shelf. Those tools help a person write code. Lathe doesn't do that.

The correct lineage is **build systems**: make, Bazel, Nix, lockfiles, reproducible-builds.org. Everything
that matters about Lathe is a build-system idea: sources compile to artifacts, artifacts are content-
addressed, the cache makes rebuilds free, you never edit object code by hand, and a red gate stops the ship.
The one new thing Lathe adds to that fifty-year lineage is this:

> **It's the first build system whose compiler is stochastic — and it makes that safe.**

A C compiler is deterministic, so nobody caches its *acceptance*. An LLM isn't, so Lathe caches the accepted
output and re-verifies instead of re-generating. That's the whole invention, and it's why the fair
competitors are Nix and Bazel (which have no stochastic-compiler story), not Cursor (which has no build
story). Nobody in either world occupies this square. Positioning consequence: stop pitching "a better AI
coding tool" and start pitching "make, for the LLM era." Different shelf, no incumbents.

There's a second reframe hiding in the plan format. A plan is specs and assert-strings; Python is just what
falls out. Squint and **the test suite is the programming language** — you program in assertions, the machine
handles syntax. People have chased "executable specifications" since the 80s (Z, VDM, literate programming,
BDD). They all failed on the same rock: someone still had to write the implementation. Lathe is the first
version of that dream where the implementation costs nothing. That's a paradigm claim worth making carefully
— and worth making.

## 2. The strongest things it does (including two nobody has noticed)

The audited strengths stand: the hard gate, the pin cache, per-function granularity, the repair loop, the
pristine tree, the validator/sandbox. Two more fell out of looking at it as a build system, and I haven't
seen either one stated — by the project or by any competitor:

**2a. The pin cache is a dataset.** Every pin is a verified (spec, tests, implementation) triple; the failure
bank is a matched set of hard negatives — what a small model got wrong and exactly which assert caught it.
Run Lathe for six months and you've accumulated, as a side effect of normal work, precisely the corpus you'd
need to fine-tune your local implementer *on your own codebase, with verification labels*. The gate is a
reward signal; the harness is an RL environment that generates its own tasks. No coding tool on the market
accumulates verified training data as exhaust. This is an asset the project doesn't know it has.

**2b. The gate is a private benchmark.** Because the pin key includes the model, you can point three
different implementers at the same plan corpus and read first-pass rate and tries-per-function straight out
of the ledger. That's a contamination-free eval on *your* tasks — not HumanEval, which every model has
memorized. Teams trying to pick a local model currently have nothing like this. `lathe bench --models a,b,c`
is maybe two hundred lines away.

## 3. Deficiencies — the sharp ones, beyond the open D-list

The §15 defects are wiring bugs. These are design-level:

- **GLUE is the untested hole in a test-everything system.** Generated functions face the gate; the
  hand-written GLUE and HEADER — the wiring, arguably the most bug-prone part — ship unverified unless a
  plan happens to have an INTEGRATION block. The system's own doctrine ("nothing ships without a test")
  doesn't apply to the code its author writes. Fix: require integration coverage for GLUE lines, or lint
  plans whose GLUE exceeds N lines without an INTEGRATION.
- **Cache invalidation is textual, not semantic.** Fix a typo in a prompt and the hash misses; the model
  re-rolls and you may get a *different* implementation for a semantically identical spec. **Fix carefully
  (Fable pass): normalize only whitespace/comments *outside string literals* and hash *both* spec and tests
  — do not demote the spec to advisory or hash tests-only.** Tests-only would turn a real semantic edit that
  no assert happens to cover (e.g. "round half-up" → "round half-even" with no .5 test) into a cache *hit*
  that silently keeps the wrong implementation — the exact stale-green bug in the next bullet. And version
  the key algorithm in the pin record (`key_version`) so an upgrade re-keys lazily on re-verify instead of
  invalidating every existing pin at once.
- **No dependency tracking between pins.** Change function A's spec and rebuild: B, which calls A, keeps its
  pin because B's own key didn't change — even though B was verified against the old A. A build system that
  doesn't track transitive invalidation will eventually ship a stale-but-green artifact. This is the classic
  make-without-depfiles bug, and it's sitting in the flagship feature.
- **Plans don't compose.** No imports, no schema version, no way to share a plan between projects except
  copy-paste. Fine at 9 plans; painful at 200. The plan format needs what every config format eventually
  needs: a version field and a module system.
- **Tests are strings.** No editor support, no coverage measurement, no linting inside the asserts. The
  source language of the whole system has worse tooling than INI files.

## 4. New ways to use it — things nobody's doing

Ranked by how far the idea is from anything shipping today:

1. **A package manager where packages ship a contract, not code.** `lathe install parse-duration` fetches a
   spec+tests (a few hundred bytes, auditable in one screen), builds it *locally on your model*, gates it,
   pins it. You review ten asserts instead of five hundred lines of someone else's tarball. **Honest framing
   (Fable pass corrected my first draft):** this doesn't make supply-chain attacks impossible — it *shrinks
   and relocates* the audit surface. Ten asserts under-constrain a function, so a poisoned spec/prompt can
   still steer the local model toward code that passes all ten and also reads `os.environ`; and the asserts
   themselves are executed code. So the trust model becomes "audit the spec+prompt, and let the sandbox bound
   what the built code can do" — which requires (a) the mutation probe to pass at install for any package
   granting I/O, and (b) install-time sandbox enforcement. With those, it's a real improvement over opaque
   tarballs; without them, it just moves the hiding place. Tessl's registry ships *docs*; this ships
   *contracts* — but a contract is only as strong as its tests.
2. **The fine-tuning flywheel (from 2a).** `lathe export-dataset` → JSONL of verified triples + failure-bank
   negatives → fine-tune the local model on its own verified history → first-pass rate climbs → cheaper
   builds generate more data. **Caveat (Fable pass): this is reward-hackable.** Gate labels are only as
   honest as the tests; fine-tuning a model on outputs it got past *its own* weak tests optimizes it to game
   those blind spots (and risks model-collapse from training on self-generated data). Do it safely: gate
   admission to the training corpus on a mutation-probe score, and hold out a human-verified eval set that is
   never trained on. With those guards it's "gets better as it ages" made mechanical; without them it's a
   model learning to fool its own grader.
3. **Model drift sentinel.** **(Fable pass corrected the mechanism.)** Verifying a pin runs stored code
   against stored tests — *no model call* — so re-verifying pins can't detect model drift; they'd stay green
   under any model. The real sentinel is *regeneration*: since the pin key includes the model, a new release
   is a cache miss — cold-rebuild the corpus under the new model and compare first-pass/tries rates against
   the old model's ledger. Rates dropping = the new model is worse on your tasks, caught before production.
   Nobody monitors *model behavior*; the pin corpus is a ready-made canary — but only via regeneration.
4. **Procurement eval (from 2b).** "Which 8-GB model should we standardize on?" is a purchasing question
   with real money attached and no good tool. A Lathe corpus answers it with your own workload.
5. **Teaching TDD backwards.** Students write the spec and tests; the machine writes the code; the mutation
   probe grades whether their tests actually pinned the behavior. The exam is the spec. Cheap to run (local
   models), impossible to cheat (the grader is a stub that tries to pass their tests).
6. **End-user compiled plugins.** Vendors ship specs; users' machines build and gate locally. No binary
   distribution, no "trust this .so" — the plugin arrives as a readable contract.

## 5. What to add — priority order for usability

1. `lathe adopt <file::func>` — brownfield entry (already §11; still the single biggest adoption lever).
2. **Semantic pin keys** (§3) — determinism shouldn't die of a typo.
3. **Transitive invalidation** (§3) — the correctness hole under the flagship.
4. `lathe bench --models` — turn the private-benchmark accident into a feature.
5. `lathe export-dataset` — turn the exhaust into an asset.
6. **GLUE coverage rule** — close the doctrine gap.
7. A tiny **plan schema** (version field, imports) before the format fossilizes.
8. Editor support: a VS Code extension that syntax-highlights assert strings and runs a function's gate
   inline. The day-to-day feel of the tool lives or dies here.

## 6. How to market it — the campaign nobody has run

The audience is engineers who distrust AI hype. The only advertising they believe is a demo they can run.
Lathe has one — but the naive version is a lie, and the Fable persona pass caught it (see appendix). Two
things break the tempting "delete the code, rebuild identical" pitch: pins *contain* the implementation
(§2a), so replaying them proves the cache is deterministic, not that specs regenerate code; and GLUE/HEADER
are hand-written and unpinned (§3), so a literal `rm -rf src/` can't come back byte-identical. Run the naive
version on stage and it prints a non-empty diff. So state the honest, still-striking version:

**The cold-rebuild demo.** Evict the cache and regenerate under the gate — the claim then has an oracle:

```
lathe verify --cold          # drop the pin cache, regenerate every function on the model, re-run every gate
                             # result: all green, and each function is byte-identical to its pin
                             # (or, honestly: "re-verifies against the same tests" if the model varies)
```

The honest headline isn't "your code rebuilds from nothing." It's **"delete the generated code and it comes
back, gated — the source was the spec, not the code you deleted."** Scope it to *generated* functions (not
GLUE), and if you want the byte-identical claim, it holds only for the pin-replay path; the cold path proves
the stronger thing (specs → passing code) but not byte-identity unless the model is fixed. A README badge
should report what it actually ran — e.g. "nightly cold-rebuild: 47/47 functions re-gated green" — not a
binary "diff empty," which (per §4.3) would also flip red on any model update and certify stale pins.

Ask Cursor, Copilot, Devin, or Tessl to run *that* — regenerate every function from its spec and pass the
gate. They can't; there are no specs and no gate. That's the real, defensible version of the demo, and it's
still a thing no competitor can do.

Supporting moves, in order:
- **Ship a repo with minimal code on main** — *once transitive invalidation lands* (§3). The pitch is a repo
  where main is mostly plans+pins and CI materializes the rest. But the Fable pass flagged the trap: with no
  transitive invalidation, a stale-but-green pin (B verified against an old A) reaches production with *no
  committed code for a human to diff-review* — the correctness hole made invisible. So: keep generated code
  committed (staleness stays diff-visible) until dependency tracking exists; then the "mostly no code on
  main" version is safe and will get argued about on every forum that matters — the arguing *is* the
  distribution. ("No source code" is also literally false while pins embed implementations; say "no
  hand-written application code.")
- **Market the refusal.** Every AI tool brags about what it generates. Lathe's benchmark story is the one
  function the gate *refused five times* rather than ship wrong. "The tool that says no" is a trust pitch no
  generator can copy, aimed straight at the roughly-half of developers who report distrusting AI output
  (Stack Overflow 2025 Developer Survey — cite it, don't quote a bare number).
- **Name the category and give away the term.** "Deterministic AI builds" / "a lockfile for AI code." Write
  the definitional post, put a one-page spec of the pin format next to it, and invite competitors to adopt
  it. If the term sticks, every conversation about the category starts at your door — the Docker playbook.
- **Spec golf.** A community game: smallest spec whose tests survive the mutation probe. Cheap to host,
  genuinely fun for the TDD crowd, and every entry is a contribution to the shared spec corpus (see 4.1).

What *not* to do: don't buy ads, don't chase the Copilot comparison, don't lead with the local-model cost
story until the benchmark is public and reproducible (per §14 of the v2 review — that number is still the
project's to prove).

## 7. Bottom line

The audits established that Lathe works. The reframe this round adds: **it's a build system, not an
assistant — the first one built for a stochastic compiler — and its two sleeping assets (the pin corpus as
training data, the gate as a private benchmark) are worth more than several of the features it advertises.**
The design-level gaps (GLUE untested, textual cache keys, no transitive invalidation) are real and should be
fixed before scale finds them. And the marketing writes itself the moment the project has the nerve to run
`rm -rf src/` in public.

---

## Appendix — how this review was itself reviewed (Fable-powered personas)

Per the standing practice: this document went through `lathe review auto` — but with the harness's persona
reviewers running on **Fable** instead of Opus. hreview hardcodes `--model opus`, so the reviewers were
routed via a PATH shim (a `claude` wrapper that rewrites the model flag to `claude-fable-5`; no repo files
modified, shim source in the commit message's session log). Run evidence: `review auto` fired the decider, which selected **correctness, adversarial, api**; three fresh
per-lens archives were written to `projects/agentic-harness/docs/ce/review_*.txt` (staggered mtimes
08:20–08:23, one per sequential Fable call). Same-model disclosure: reviewer and reviewed are both Fable;
treat it as an adversarial second read, not an independent oracle.

**The Fable pass was materially sharper than the Opus passes on prior rounds — it found cascading,
cross-section contradictions, not just local nits.** Every finding was folded in above; the load-bearing ones:
- **CRITICAL:** the `rm -rf` demo contradicted §2a/§3 (pins contain code; GLUE is unpinned) → rewrote it as
  the honest cold-rebuild demo.
- **HIGH:** "package with no code = no supply-chain risk" is false (weak asserts under-constrain) → reframed
  as shrinking/relocating the audit surface, gated on mutation-probe + sandbox.
- **HIGH:** the fine-tuning flywheel is reward-hackable / model-collapse-prone → added held-out-eval and
  mutation-gated-admission guards.
- **HIGH:** no-code-on-main + no transitive invalidation = invisible stale-green → gated the recommendation
  on transitive invalidation landing first.
- **MEDIUM:** drift sentinel via pin *verification* can't work (no model call) → corrected to regeneration.
- **MEDIUM:** semantic pin keys as first drafted (tests-only) would *worsen* stale-green → corrected to
  normalize-whitespace-only + hash-both + versioned key.
- **LOW, self-directed:** the PATH shim's blast radius could poison the model-keyed pin ledger. Checked:
  `lathe review` writes no pins, and no `.pins.json` changed during the shim window — ledger clean. Shim
  should still be scoped to the reviewer subprocess, not global PATH, in any repeatable setup.
