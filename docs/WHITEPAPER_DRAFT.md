# The discipline you already believe in — enforced by the machine

*(working title; alt: "You'd never hand-patch a compiler. Hold AI code to the same contract.")*

*A draft rewrite of the Lathe whitepaper, authored by the round-7/8 reviewer (Fable) per the maintainer's
request. This is the manifesto — method-level, evergreen. The versioned technical paper (architecture,
threat model, pin-format spec, raw benchmark data) should live separately; see the outline at the end.
Facts below that carry audit weight are cross-referenced to the review documents in this repo; everything
else is argument, and is written to be argued with.*

---

## 1. You already know the problem

You've watched an AI coding session rot. Brilliant for ten minutes, then the drift: ask twice, get two
different answers; thirty messages in, your earlier decisions are quietly contradicted; the model tells
you something works when it doesn't. You hand-fix one file and now nothing can be regenerated. By the end
you have a pile of code that happens to work right now — and no way to rebuild it, reason about it, or
trust it tomorrow.

The numbers agree with your scars. Roughly half of surveyed developers say they actively distrust AI
output; the top complaint is code that's *almost* right. A 2025 study ran 300 AI-generated projects in
clean environments: only 68% even executed. Maintainers of major open-source projects are shutting down
bug-bounty programs under a flood of plausible, wrong, machine-written patches.

The industry's answer has been bigger models and better vibes. Ours is different.

## 2. A conversation is not a build

You can't rebuild a conversation. You can't diff it, pin it, or trust it to come out the same twice. Every
mainstream AI coding tool — the assistants, the agents, the IDEs — is a conversation with better tooling.
The output is unreproducible by construction, unverified by default, and owned by no process once a human
starts hand-patching it.

Before AI, we didn't ship software that way, and the reasons we didn't haven't changed. You keep the
source, not the binary. You write the test, then the code that passes it. You don't merge red. You commit
a lockfile. Every bug becomes a test.

Lathe is those habits, pointed at an LLM. Not a smarter model — a refusal to treat generation as a chat.

## 3. You already believe in this. You just skip it on Friday.

None of the good practices are new, and you already trust them:

- **Test-first (TDD).** Write the test, then the code that passes it. Kent Beck made it mainstream in 2003;
  every serious team says they do it.
- **Never merge red.** Continuous integration with a required green build — no override, no "just this once."
- **Independent review.** A second pair of eyes on every change, formalized as the pull request.
- **Locked, reproducible builds.** `yarn.lock`, `pip freeze`, Nix — everyone's build is identical.
- **The compiler contract, the deepest one:** nobody hand-patches a compiler's output. If the binary is
  wrong, you fix the source and recompile.

These didn't die. They *erode* — under deadline pressure, on a Friday afternoon, with a `--no-verify` and a
rubber-stamped approval. They run on willpower, and willpower loses to shipping. The whole reason your AI
code is "almost right" is that the discipline that would catch it is the first thing dropped when it's
tedious, and AI made writing code so cheap that the tedious part is now the whole job.

Lathe's move is not to invent discipline. It's to make the discipline you already believe in **unskippable**
by moving it off willpower and onto the machine: the gate refuses red, the pin locks the build, the tree
rejects a dirty commit, and — the compiler contract, extended to LLMs — you never hand-edit the output;
wrong code means a wrong spec, so you fix the spec and rebuild.

![The discipline you already believe in — enforced](infographics/11_discipline_enforced.png)
*Four practices every working developer already trusts — test-first, never merge red, locked builds, don't
hand-patch the compiler — moved from "runs on willpower" to "enforced by the build."*

There is an older, deeper ancestor for the specific shape of this — IBM's Cleanroom Software Engineering
(Mills, 1980s: implementers who don't debug, an independent team that certifies, statistical quality
control). It's the honest intellectual lineage and it's in `PRIOR_ART.md` for the people who care. But you
don't need to know it to recognize what Lathe does. It's `make` and a lockfile and a green build and TDD —
enforced, not merely encouraged.

## 4. The method

Four artifacts, four rules.

**The artifacts:**
- **The plan** — the source of truth. Per *function*: what it should do (the spec) and the asserts that
  prove it (the tests). Written by the analyst — a frontier model or a human. Plans are data, validated
  before anything runs.
- **The gate** — an isolated sandbox that runs the tests against the generated code. Its verdict is
  cryptographically framed (a nonce the tested code never sees), so a malicious test can't print a fake
  pass. Pass → accept. Fail → refuse. There is no "looks done."
- **The pin** — accepted code is stored under `hash(spec + tests + model)`. An unchanged plan rebuilds
  byte-identically with **zero model calls**. The model is random; the pin makes the *build* deterministic
  — reuse, don't re-roll.
- **The ledger** — every run logged, every failure banked with the exact assert that caught it, every
  accepted function carrying its full provenance: which spec, which tests, which model, when.

**The rules:**
1. **Never hand-edit generated code.** It's a build output. The moment you patch it, reproducibility dies
   and you own the debt. Wrong output means a wrong spec — fix it upstream and rebuild.
2. **Never escalate.** When the cheap model fails, the analyst sharpens the *spec*, not the model bill.
   This looks like cost dogma; it's actually a clarity mechanism. A weak implementer is a spec linter: a
   frontier model papers over ambiguity by guessing well, a small one exposes it. Specs that survive this
   loop are unambiguous — to models and to the humans who read them later.
3. **The tests are the contract — and the process, not the model, decides how thorough they are.** A
   function is done when its asserts pass in the sandbox. Beyond that floor, a set of gates you can switch on
   (`LATHE_STRICT=1` composes them) move testing thoroughness from discretion to enforcement: every declared
   acceptance criterion must map to a named test (traceability, with `lathe trace` emitting the
   requirement→test→pin→model matrix); a bug fix must ship a test that *fails on the old code* before it's
   accepted (regression-proof); and accepted code is mutated and rejected if the suite can't tell the real
   thing from a broken copy (mutation-score). Stated against interest: the mutation gate is a **bounded
   tripwire for vacuous tests** — a small operator set, capped per function, equivalent mutants excluded so it
   never false-blocks correct code — *not* exhaustive coverage, and it measures one gated function's test
   adequacy, not the whole system. Glue stays hand-written and ungated. So: *the code Lathe gates is
   comprehensively tested by construction* — not *your whole system is.*
4. **The tree stays pristine.** One canonical implementation per capability, no stale copies, no dupes —
   enforced by gates that fail the build, not by convention. An agent (or a new hire) reading this tree
   never has to guess which of three `util.py`s is real.

The loop, in one breath: *analyst writes spec+tests → local model implements → gate accepts or refuses →
accepted code is pinned → failures flow back as sharper specs.* Big model for judgment, small model for
volume, machine for discipline.

![The build loop](infographics/01_build_loop.png)
*Goal → analyst → implementer → gate → pin, with the failure path looping back to a sharper spec.*

![Division of labour: analyst versus implementer](infographics/02_division_of_labor.png)
*Big model or human for judgment; a cheap local model for volume; the gate for discipline — pluggable at
both ends.*

## 5. What it looks like

A real plan entry — this shipped:

```python
{
  "name": "_is_standalone_word",
  "prompt": "Return True if `word` appears as a whole word in `text`, else False. "
            "Use a regex word boundary.",
  "tests": [
    "assert _is_standalone_word('director','associate director') == True",
    "assert _is_standalone_word('analyst','data analytics') == False",
  ],
}
```

That's the whole programming model: you write *what* and *prove-it*; the machine writes *how*. Functions
compose into modules, modules into ordered plans, integration tests guard the seams. Delete the generated
code and rebuild: for pinned plans it comes back byte-identical without a model call; cold-rebuild it and
every function regenerates and re-passes its gate. The code was never the source.

![Determinism you can prove](infographics/15_determinism_two_claims.png)
*Guaranteed: a pinned rebuild is byte-identical at zero tokens. Not claimed: regeneration may differ — but
still passes the same gate. Determinism is a property of the build, not the model.*

## 6. A new number: provenance coverage

Test coverage told the 2000s how much of the code was exercised. The AI era needs a different number:
**what fraction of your shipped lines carry full provenance** — a spec, the tests that accepted them, the
model that wrote them, the hash that pins them. Call it provenance coverage.

Copilot-style tools score 0% by construction: there is no artifact linking a generated line to an
acceptance criterion. Lathe-built modules score 100% by construction. Most real repos will sit in between
— and the number is honest about the boundary: hand-written glue is hand-written, and says so.

![Provenance, by construction](infographics/14_provenance_chain.png)
*The chain each function carries — requirement → spec → tests → gate → model → hash — machine-generated at
build time. (Requirement link when criteria are declared; the verdict is proven by the pin.)*

We hold ourselves to the same metric, and today the honest number for Lathe's own tree is low — the engine
that enforces the gate was not itself built through the gate. That's the ceiling of the current method
(it industrializes well-specified functions, not stateful plumbing), and we'd rather publish the
embarrassing number and make it climb than pretend. Track ours in the repo.

## 7. Evidence — and the limits, stated against interest

![The methodology, enforced by the build](infographics/13_methodology_enforced.png)
*The three enforcement gates — traceability, regression-proof, mutation-score — composed by `LATHE_STRICT=1`.
The bottom band states the scope against interest: a bounded tripwire, per function, not whole-system.*

What's demonstrated, reproducibly, in this repo:
- **Reproducibility:** pinned rebuilds are byte-identical with zero model calls (CI proves it on every
  commit; you can prove it in one command).
- **The gate refuses.** In the first real-hardware run (a 9B, 4-bit local model; specs and tests held
  fixed), 7 of 8 functions passed within five attempts, 6 of 8 first-try — and the one function the model
  couldn't implement was *refused five times* rather than shipped wrong. The refusal is the product.
- **Security holds under audit:** the plan validator and the sandbox's unforgeable-verdict design survived
  six adversarial review rounds, and the review artifacts — including every finding against us — are
  committed in this repo.

What's *not* yet demonstrated, so you don't have to discover it yourself:
- The cost/quality claim — that a cheap local model carries real production workloads — has one small
  benchmark behind it, not a public, metered, reproducible one. It's coming; until then treat the
  economics as a design you can test in an afternoon, not a proven result.
- The method's unit is the well-specified function. Stateful, I/O-heavy, framework-shaped code doesn't
  decompose that way yet; glue is hand-written and only as tested as your integration blocks.
- On trivial tasks, a frontier one-shot is faster. Our own benchmark says so (41s vs 5s). Lathe buys
  verification, reproducibility, and provenance — not speed of first draft.

A note on trust: parts of this project's own review history were produced by AI reviewers and then
*contradicted by evidence* — including a root-cause story the git history disproved. We kept those
corrections in the record on purpose. The documentation tells the truth against interest; that is the
project's actual brand, and this paper is written under the same rule.

## 8. Where this goes

The pin ledger is more than a cache. It's a verified dataset (every pin a spec→tests→code triple — the
raw material for fine-tuning your local model on your own gated history); a private benchmark (point two
models at the same plans; the ledger scores them on *your* work, not on a leaderboard they memorized); and
a traceability matrix (requirement → spec → test → code → model — the artifact regulated industries
currently assemble by hand at enormous cost). None of that requires new machinery. It's all exhaust from
building the disciplined way.

## 9. Try it

```
pipx install lathe-harness          # or clone the repo
lathe build examples/hello.py       # pinned demo: rebuilds offline, zero model calls
lathe verify examples/hello.py     # prove the byte-identical claim to yourself
lathe do "a function that parses '2h30m' into seconds"   # the full loop, with your endpoints
```

Then write one plan of your own — one function, one spec, three asserts — and watch the gate accept or
refuse. That single loop is the whole idea in your hands.

---

*Technical companion (separate, versioned document): architecture and data flow; the plan grammar; the
validator's closed rules; sandbox tiers and the verdict protocol; pin-format specification; benchmark
methodology and raw data; threat model and known limits. Engineers trust appendices; the appendices are
there.*
