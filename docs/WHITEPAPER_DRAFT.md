# Discipline used to be expensive. Now it compiles.

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

## 3. The part everyone forgot: we already solved this

Here is the section no other AI-tools paper can write, because every other paper starts in 2022.

In the 1980s, IBM's Cleanroom Software Engineering produced some of the lowest-defect software ever
measured. Its rules sound alien now: **developers never execute their own code.** Construction and
verification are separate roles. Nothing ships without independent certification. Cleanroom worked — and
it died, because paying humans to work that way cost too much for all but spacecraft and pacemakers.

The V-model said: every requirement gets a design, every design gets a test, every test gates a stage.
Fagan inspections said: a second pair of eyes, formally, every time. Requirements traceability said: every
shipped line answers to a numbered requirement. All of it worked. All of it was priced in human hours, and
the industry spent forty years discounting it toward zero.

**The economics just flipped.** A model can be the implementer who never judges their own work. A sandbox
can be the independent certifier. A hash can be the traceability matrix. The most disciplined methodology
ever invented was too expensive for humans — and is now nearly free.

That's what Lathe is. Not a new idea. The oldest good idea, repriced.

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
3. **The tests are the contract.** A function is done when its asserts pass in the sandbox, and a spec is
   suspect if a trivial stub can pass its tests (a mutation probe checks exactly that).
4. **The tree stays pristine.** One canonical implementation per capability, no stale copies, no dupes —
   enforced by gates that fail the build, not by convention. An agent (or a new hire) reading this tree
   never has to guess which of three `util.py`s is real.

The loop, in one breath: *analyst writes spec+tests → local model implements → gate accepts or refuses →
accepted code is pinned → failures flow back as sharper specs.* Big model for judgment, small model for
volume, machine for discipline.

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

## 6. A new number: provenance coverage

Test coverage told the 2000s how much of the code was exercised. The AI era needs a different number:
**what fraction of your shipped lines carry full provenance** — a spec, the tests that accepted them, the
model that wrote them, the hash that pins them. Call it provenance coverage.

Copilot-style tools score 0% by construction: there is no artifact linking a generated line to an
acceptance criterion. Lathe-built modules score 100% by construction. Most real repos will sit in between
— and the number is honest about the boundary: hand-written glue is hand-written, and says so.

We hold ourselves to the same metric, and today the honest number for Lathe's own tree is low — the engine
that enforces the gate was not itself built through the gate. That's the ceiling of the current method
(it industrializes well-specified functions, not stateful plumbing), and we'd rather publish the
embarrassing number and make it climb than pretend. Track ours in the repo.

## 7. Evidence — and the limits, stated against interest

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
