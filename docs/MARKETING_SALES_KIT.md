# Lathe — marketing & sales kit

*Authored by Fable per the maintainer's request. Grounded in `CAPABILITY_MAP.md` (what's real) and
`PRODUCT_STRATEGY.md` (where to aim). Rule for everything in this file: no claim that the repo can't back.
The unproven claims (local-model economics at scale) are framed as invitations to test, never as results.*

---

## 1. Positioning

**Category (own it):** Deterministic AI builds. A build system, not an assistant.

**Positioning statement:** Everyone ships tools; Lathe ships enforcement. The practices you already believe
in — test-first, never-merge-red, locked builds, don't-hand-patch-the-compiler — made unskippable by a
machine that can't be talked out of them under deadline. (Anchor on TDD/CI/lockfiles/the compiler contract,
which every working dev knows — not on obscure 1980s methods. See `GRAPHIC11_FACTCHECK.md` for why.)

**One-liner:** Stop chatting with the AI. Build with it.

**Now sayable (as of v2.2.1 — verified, cleared in `METHODOLOGY_ENFORCEMENT_VALIDATION.md`):** *test
comprehensiveness is measured and gated, not assumed.* Three enforcement gates — requirement→test
traceability, a bug fix must ship a test that fails on the old code, and a mutation-score that rejects a
suite that can't tell the code from a broken copy — composed by `LATHE_STRICT=1`. **Mandatory scope clause,
always attach it:** the mutation gate is *"a bounded tripwire for vacuous tests (small operator set, capped
per function, equivalent mutants excluded), not exhaustive coverage"*, and it gates *each function, not your
whole system* (glue stays ungated). Say "the code Lathe gates is comprehensively tested," never "your whole
system is."

**Tagline bank** (pick per surface, don't use all):
- You'd never hand-patch a compiler's output. Hold AI code to the same contract.
- The discipline you already believe in — enforced.
- The tool that says no.
- Same spec, same code, every time.
- Your tests are the language. The code is a build artifact.
- Delete the generated code. It comes back, gated.

*Retired (do not use): "Discipline used to be expensive. Now it compiles." — the underlying "these
disciplines died / developers never tested their own code" premise is false; a skeptical engineer will
screenshot it. Fact-check in `GRAPHIC11_FACTCHECK.md`.*

## 2. Pitches, by length

**10 seconds:** "It treats AI codegen like a compiler with a test gate: specs and tests in, verified code
out, byte-identical on every rebuild. If the tests don't pass, the code doesn't ship — period."

**30 seconds:** "Every AI coding tool generates code you then have to review and babysit, and no two runs
give the same answer. Lathe inverts it: a frontier model writes a per-function spec and tests, a cheap
local model writes the code, a sandbox runs the tests, and only passing code is accepted — then it's
content-hash pinned so rebuilds are byte-identical with zero model calls. You never hand-edit output; you
fix the spec. It's make and a lockfile for the LLM era."

**2 minutes (add):** the no-escalation repair loop (failures sharpen the spec — which is also why the
specs end up readable by humans); the pristine-tree gates (one canonical implementation per capability, so
an AI agent never patches the wrong copy); provenance by construction (every line traces to spec + tests +
model + hash); runs standalone, inside Claude Code/Cursor via MCP, or embedded; any model in either role,
local by default. Close with the honest bit: "On easy tasks a frontier one-shot is faster — our own
benchmark says so. You buy verification, reproducibility, and provenance, not speed of first draft."

## 3. Pitches, by audience

**The skeptical staff engineer** (lead with mechanism, never adjectives):
"Two claims, both checkable in your terminal in five minutes. One: rebuilds are byte-identical with zero
model calls — clone the repo, run `lathe verify examples/hello.py`, watch the pins. Two: the acceptance
gate can't be forged — the sandbox nonce-frames its verdict; read `sandbox.py`, it's 250 lines. Everything
else is a corollary."

**The platform / compliance director** (lead with the audit trail):
"Your AI-generated code currently has no provenance: nobody can say which model wrote a line or what
acceptance criteria it passed. Every function Lathe ships carries exactly that — requirement → spec →
test → code → model → hash — by construction, not by after-the-fact paperwork. When CRA/AI-BOM obligations
land in 2026–27, this is the artifact your auditors will ask for, and today no other tool can produce it."

**The local-LLM builder** (lead with the economics-as-experiment):
"Your 9–12B model is bad at open-ended agent work and genuinely good at one well-specified function at a
time — that's the regime Lathe puts it in, with a gate so its mistakes can't ship. Run your model against
our plan corpus and the ledger tells you your first-pass rate. Free per token, private by default."

**The CTO** (lead with risk, close with the metric):
"Half your engineers distrust AI output and the other half ship it unreviewed. We make the machine hold
the review line: nothing merges red, everything reproduces, every line has provenance. Ask any vendor one
question: *what fraction of your generated code carries a verifiable acceptance record?* Our answer is
100% by construction. Everyone else's is zero."

## 4. The demo script (the honest cold-rebuild)

1. Show a built module. `git log` it — provenance marker, pin entry.
2. Delete the generated functions. Rebuild **from pins**: byte-identical, zero model calls, seconds.
   "The code was never the source."
3. Now evict the cache and **cold-rebuild**: every function regenerates on the model and re-passes its
   gate, live. "Different bytes, same contract — and the gate decides, not the model's confidence."
4. Break a spec's test on purpose. Watch the gate refuse five times and the analyst sharpen the spec.
   **"The pitch isn't that it writes code. The pitch is that it refuses wrong code."**
5. Close on the ledger: `lathe metrics summary` + the pin file. "This is your provenance record and, later,
   your model benchmark and your fine-tuning dataset. It's exhaust — you get it for building the right way."

Never run the naive `rm -rf src/ && diff` version on stage — GLUE/HEADER are hand-written and unpinned;
the diff won't be empty and a skeptic will notice (details: `LATHE_REVIEW_V3_FABLE.md` §6).

## 5. Objection handling

- **"The gate is only as good as the tests — and the tests are AI-written too. Garbage in, garbage out."**
  The sharpest objection, and we answer it at *both* ends — with a two-stage front end. **Front end (goal):**
  `lathe clarify` interrogates the goal for ambiguity *before* the harness thinks — fewest, sharpest questions
  with pick-from options — and writes testable acceptance criteria. **Front end (spec):** an adversarial
  `assumption-auditor` (v2.5.0) then re-reads the spec against the goal and surfaces every decision the goal
  never made — encoding, rounding, ordering, empty-input behavior — refusing to build while any *material*
  guess is unconfirmed (scrutiny dial-able `off`→`all`; the seventh STRICT gate). Ambiguity is dragged out
  with the user up front, not discovered in prod. **Back end:** the tests themselves are gated — mutation-score
  rejects a stub-passable test, `#5` enforces the required *kind* of test per contract (property/edge/error),
  regression-proof needs a failing-on-old-code test, and test-ack forces a human read. *Honest limit:* it's
  a shift and a hardening, not elimination — `clarify` surfaces ambiguity, it can't guarantee the user's
  answers are right; example tests remain gameable. The frame is "much harder to fool," not "unfoolable."
- **"LLMs aren't deterministic; 'same code every time' is impossible."** Correct — and we don't tame the
  model, we sidestep it. Accepted output is pinned by content hash; rebuilds replay the pin with no model
  call. Determinism is a property of the *build*, not the model. (This objection is our favorite: answering
  it *is* the pitch.)
- **"Writing per-function specs is more work than writing the code."** For code you'd dash off in a
  minute, yes — our benchmark says a one-shot is faster on trivial functions, and we published that. The
  spec pays where correctness, reuse, or audit matters: you write the contract once and the implementation
  is free forever after, on any model. Also: you already write this — they're called tests; here they're
  just written first and enforced.
- **"My code isn't pure functions."** The honest limit. Lathe industrializes the well-specified core;
  glue and I/O stay hand-written (and are marked as such in the provenance number). It's a leaf-function
  factory today. If your codebase has no such core, it's not for you yet.
- **"Why not just Copilot/Cursor?"** Different job. They optimize writing speed; nothing they produce is
  reproducible, gated, or attributable. Use them to *draft plans* if you like — Lathe is the layer that
  decides what ships. (Via MCP, they can literally drive it.)
- **"Is a local 12B actually good enough?"** The design says yes for gated single functions; the public
  evidence is one small run (7/8 within five tries, and the failure was *refused*, not shipped). We won't
  claim more until the reproducible benchmark is published. Run your own corpus — the ledger will tell you
  in an afternoon.
- **"Open source with one maintainer — will this exist in two years?"** MIT license, a few thousand lines
  of stdlib-only core, your pins and plans are plain files in your repo. Worst case you fork it and it
  keeps working. Compare the lock-in of any cloud assistant.

## 6. Compliance one-pager (the paying niche)

**Header:** Provenance-grade AI code generation, for teams that answer to auditors.
**Problem:** regulators (EU CRA 2026–27, AI-BOM procurement, emerging insurance exclusions for
gen-AI-written code) are converging on one question — *prove how this code was produced and verified.*
Cloud assistants cannot answer it; banning AI leaves the productivity on the table.
**Answer:** every Lathe-built function carries requirement → spec → test → sandbox verdict → model ID →
content hash, machine-generated at build time. Traceability is not a report you assemble; it's a property
of the artifact. Local-first execution keeps source inside your boundary; the gate keeps unverified code
out of it.
**Ask:** a two-week pilot on one module family; deliverable is the traceability matrix your QA team
currently builds by hand.

## 7. Launch assets

**HN title candidates** (pick the concrete one, not the clever one):
- "Lathe: content-hash-pinned, test-gated code generation on a local model"
- "A build system where the compiler is an LLM and the lockfile actually works"
- "We made AI codegen reproducible by refusing to let it be a conversation"

**Launch post skeleton:** the scars (§1 of the whitepaper) → one real plan → the loop → `verify` proving
byte-identity → the refusal story → the losses (benchmark where we're slower; what's unproven) → "here's
everything, MIT, break the sandbox and we'll pay you" (link the forgery bounty when live).

**Recurring channel:** model-release-day scoreboard (every new local model, same plan corpus, publish
first-pass rates same-day). See `PRODUCT_STRATEGY.md` §8.

## 8. Guardrails — what we never claim

- Never "AI you can trust" unqualified → always *"code you can verify."*
- Never imply the local-model economics are proven at scale → *"the default is free and local; here's how
  to measure it on your work."*
- Never present 🔌 capabilities (MCP, mutation probe, skeleton-fill…) as the shipped autonomous path —
  status per `CAPABILITY_MAP.md`.
- Never hide the losses. The benchmark where Lathe is slowest is in the repo on purpose; cite it before
  the skeptic finds it. The project's moat is that its documentation tells the truth against interest.
