# Lathe — Presentation Design Brief

> **Hand this to Claude Design.** It contains everything needed to design a presentation that explains
> Lathe to real developers: the story, the full copy (already written in human voice), the proof, the
> brand system, and the hard-won lessons about what *not* to do. Design the experience; the substance is here.

---

## 0. The one-line ask

Design an **interactive, story-driven presentation** (a scrollable/clickable web deck, ~20 "slides") that makes a
working developer *feel* why Lathe matters in about two minutes — structured as **problem → the many ways we
fix it → proof it's real** — in language that sounds like a developer talking, not a spec sheet.

---

## 1. What Lathe is

Lathe treats **AI code generation like a build system, not a conversation.** You don't chat with a model and
hope; you hand it a contract (a spec + tests), a cheap local model writes the code, gates judge it, and passing
code is **pinned** so rebuilds are byte-identical. Every failure sharpens the spec instead of summoning a bigger
model.

**The thesis (the spine of the whole presentation):**
AI codegen is **non-deterministic** — same prompt, different code; confident when it's wrong; unreproducible;
unaccountable. Lathe makes it **deterministic**: the same inputs produce the same *proven* output, every time.
And because AI fails in so many different ways, **each problem is attacked from several angles at once** — the
redundancy is the product. *"Ensured many ways, not one."*

**The banner name:** the user is choosing between **"Deterministic AI"**, **AID**, and **D·AI**. Current lean:
lead with the plain-English promise — **"AI you can actually depend on"** — and keep **AID** as a compact mark.
(Open question — see §12.)

---

## 2. Who it's for — and the VOICE MANDATE (read this twice)

**Audience:** software developers who build with their own hands and have been burned by AI codegen. They've
shipped the confident-but-wrong bug. They've watched an agent edit the wrong file. They don't trust marketing.

**The single most important rule of this project:** *write for humans, in their own language.*

Earlier drafts failed because they read like a datasheet — "content-hash pin," "nonce verdict," "ADV_SYNTH,"
"gates fail closed," "requirement→test traceability." That is language for a machine to parse. It has to be the
language of a developer explaining it to a teammate over coffee.

**Do:**
- Short, concrete, a little wry. Name the feeling ("You got the perfect output yesterday. Today it's gone.").
- Lead with the plain-English meaning; hide the internal/technical name (or drop it entirely).
- Second person. Active voice. Real scenarios (`'€5'`, an empty file, `util_final_OLD.py`).

**Don't:**
- No acronyms on the face of a slide. No "acceptance criteria," "verdict," "adversarial probes," "provenance
  chain" as *headlines*.
- No one-idea-per-slide feature list that reads as repetitive.

**The rewrite, illustrated** (this is the target register):

| ❌ Spec-speak (what failed) | ✅ Human voice (the target) |
|---|---|
| "Nonce verdict — the pass/fail is unforgeable" | **"It can't fake a passing grade."** It can't just print 'all tests passed' and slip by — the pass is checked where the AI can't reach. |
| "Test-quality linter (mutation probe)" | **"It checks your tests are real."** It quietly breaks the code on purpose. If your tests don't scream, they weren't testing anything. |
| "ADV_SYNTH adversarial bypass probes" | **"It tries to break its own code."** Before shipping, it writes sneaky inputs to attack the code — and the code has to survive them. |
| "Required test-kind per contract" | **"Did you test the ugly cases?"** It won't let you skip the empty input, the bad input, the edge — the ones that actually bite. |
| "Assumption gate (materiality-ranked)" | **"It lists what you left unsaid."** Every decision your goal didn't make gets laid out and ranked. The risky ones stop the build. |

---

## 3. What this presentation must accomplish

- In ~2 minutes of clicking, a skeptical developer **gets it** and wants to try it once.
- It must **feel like one interconnected system**, not a bag of features. The "many angles on one problem"
  visual is how we sell the depth.
- It must **prove itself** — claims are backed by real commands and real output (very on-brand: Lathe's whole
  premise is claims backed by evidence). See §6.
- Honest throughout. Where something needs a live model to demonstrate, say so (see §6, §9).

---

## 4. The narrative structure (the skeleton)

```
OPENER  →  [ Problem 1 → How we fix it (arsenal) → Proof ]
           [ Problem 2 → arsenal → Proof ]
           ...
           [ Problem 6 → arsenal → Proof ]
        →  CLOSER
```

- **6 problems** every AI-codegen user hits (not a feature list — real pains).
- Each problem is followed by an **"arsenal" screen**: the *multiple* mechanisms that attack that ONE problem,
  converging on it. This is the core visual idea — **watch 4–9 defenses assemble around a single failure.** It
  literally shows "ensured many ways, not one."
- Each arsenal is followed by a **proof screen**: a real terminal command + its real output + a plain verdict.

~20 screens total: 1 opener + 6×(problem + arsenal + proof) + 1 closer.

---

## 5. Brand & visual system

**This is an established visual identity** — the presentation must feel continuous with Lathe's existing
infographics (see §7). Match it; don't invent a new look.

### Palette (warm, hand-built, "workshop" feeling — not a cold SaaS gradient)
| Token | Hex | Use |
|---|---|---|
| Cream (ground) | `#F4EEE1` | page / light background |
| Ink | `#3D2B22` | primary text, dark terminal bars |
| Teal (accent) | `#7EA8A1` (deepen to `#5f8c84` for text-contrast) | eyebrows, links, active state |
| Coral | `#E4986B` | emphasis, the "wrong/pain" hue, one accent pop |
| Sage | `#8DB26A` | "pass / fixed / good" |
| Amber | `#D9A441` | "warning / pending / opt-in" |
| Muted grey | warm grey biased toward ink | neutrals |

Semantic: **coral/red = the problem**, **sage/green = the fix works**, **amber = pending / needs-a-live-model.**
Dark theme required (deep warm brown ground `#1f1712`, not black); design both themes with equal care.

### Typography
- A clean humanist **sans** for narration (system-ui is fine; the CSP blocks web-font CDNs, so if a custom face
  is wanted it must be embedded as a data-URI, not linked).
- A **monospace** doing real character work — it's a *build tool*, so the terminal/console voice matters. Use
  mono for: commands, file names, hashes, the terminal cards, small eyebrow labels.
- Big, confident display weight for problem headlines. `text-wrap: balance`.

### The signature visual: "the convergence"
The arsenal screen shows the **problem as a red node**, and the **mechanisms as cards that fly in and lock onto
it** — 4 to 9 of them, staggered. The emotional beat: *"look how many independent nets there are under this one
bug."* End each with a **sage payoff bar** stating the win in one human sentence.

### The proof aesthetic
A **realistic terminal card** (dark, three traffic-light dots) with a `$ command` in amber, output below,
success lines in green. Then a green **verdict pill** in plain English ("Rebuilt with no AI and no tokens —
identical to before.").

### Motion
One orchestrated arc per screen (cards rise + stagger; the gate flips red→green; a token counter falls to 0).
Respect `prefers-reduced-motion`. Don't over-animate — restraint reads as craft.

---

## 6. THE STORY, IN FULL (copy is ready — polish, don't rewrite the register)

Each chapter = **Problem copy → Arsenal (mechanisms) → Payoff → Proof.**
For each mechanism: **human title** · *what it means* · `(internal name — for the designer only, don't surface)`.
Proof status: ✅ = captured real output (below) · ⏳ = needs a live model (flag honestly, amber).

---

### OPENER
- Eyebrow: *every developer knows this feeling*
- Headline: **"AI writes code fast. You just can't trust it."**
- Body: *Ask it twice, you get two different answers. It sounds sure of itself when it's dead wrong. And you
  can't rebuild what it made yesterday. Lathe treats AI like a **build tool, not a chat** — so what comes out is
  tested, repeatable, and yours. The trick isn't one clever safety net. It's a dozen, all watching each other.*
- Mark: **AID** — *"AI you can depend on. Same input, same trustworthy result — every time."*

---

### CHAPTER 1 — "The slot machine"
**Problem — "Ask it twice, get two different answers."**
*You got the perfect output yesterday. Today the same prompt gives you something else. You can't rebuild what it
made, can't hand a teammate the exact same code, can't lock it down. It's a slot machine — and you're feeding it
your codebase.*
Pain chips: `yesterday: worked` · `today: different` · `can't get it back`

**Arsenal — problem node: "You can't reproduce what it made"** (4 angles)
- **It remembers exactly what it built** — Ask for the same thing and it hands you the same file back, no AI
  call, no wait, no cost. `(content-hash pin)`
- **Delete the code, get it right back** — Rebuild and it replays what already passed, down to the byte, free.
  `(zero-token replay)`
- ★ **Old work can't coast on a weaker bar** — Tighten your checks and yesterday's code gets re-checked; it
  can't sneak by on the old rules. `(regime-aware pins)`
- ★ **It can rehearse the whole run offline** — Record a run once and replay it forever, same result, no live AI
  needed. `(cassette record/replay)`

**Payoff:** *The AI is a slot machine. The build isn't — same inputs, the exact same code, every single time.*

**Proof ✅** — claim: *"Delete the code, rebuild it — same bytes, zero cost."*
```
$ lathe verify examples/hello.py
  building the page ...
  REPRODUCIBLE — 1/1 unit reused from pins (byte-stable, 0 model calls)
  tokens used: 0   ·   AI calls: 0   ·   source: pinned
```
Verdict: *Rebuilt with no AI and no tokens — identical to before.*

---

### CHAPTER 2 — "Confidently wrong"
**Problem — "It's wrong — and it's completely sure of itself."**
*The code reads beautifully. It's also quietly wrong on the one input you didn't think to check. And the tests?
Half of them pass no matter what the code does — they were never really testing anything.*
Pain chips: `reads great` · `breaks on '€5'` · `tests that test nothing`

**Arsenal — problem node: "It ships broken code that looks fine"** (9 angles — the showcase screen)
- **The tests are the boss** — Fail one and the code doesn't ship. The AI doesn't get to explain its way out.
  `(hard test-gate)`
- **You set 'done' before it writes a line** — The tests come first; they're the finish line, and you draw it.
  `(tests-first)`
- **It can't fake a passing grade** — It can't print 'all tests passed' and slip by; the pass is checked where
  the AI can't reach. `(nonce verdict)`
- **It checks your tests are real** — It quietly breaks the code on purpose. If your tests don't scream, they
  weren't testing anything. `(mutation-score)`
- **It catches tests that test nothing** — If a do-nothing stub passes your tests, you're told before a line of
  code is written. `(spec-lint)`
- **Did you test the ugly cases?** — It won't let you skip the empty input, the bad input, the edge. `(test-kind)`
- ★ **It tries to break its own code** — Before shipping, it writes sneaky inputs to attack the code, and the
  code has to survive them. `(ADV_SYNTH)`
- ★ **A broken check never waves you through** — If a safety check can't run, it says no. No news is never good
  news here. `(gates fail closed / tri-state)`
- ★ **A room of experts reads it** — A security reviewer, a bug-hunter, a reliability stickler, each reads the
  change with their own eyes. `(CE review personas)`

**Payoff:** *Nine different ways to catch a bad line — and it even makes sure your tests are actually testing
something.*

**Proof ✅** — claim: *"It really does make sure your tests are worth anything."*
```
$ python review_tests/test_mutation_score.py
  breaking the code on purpose, checking the tests notice...
  mutation-score acceptance: ALL PASS
```
Verdict: *The 'are your tests real?' check is itself tested and passing.*
Note (honest): *The 'prove-the-bug-first' check runs inside a live build — shown once the model's up.*

---

### CHAPTER 3 — "The silent guess"
**Problem — "It guesses — and never mentions it."**
*You didn't say how to handle an empty file, or which way to round, or what counts as 'done.' So it just… picked
something. Didn't ask, didn't flag it. You find out when a customer does.*
Pain chips: `empty input? guessed` · `rounding? guessed` · `you find out in prod`

**Arsenal — problem node: "It fills the gaps and stays quiet"** (6 angles)
- **It asks what you forgot to say** — Vague goal? It interviews you first — inputs, edge cases, what 'done'
  means — before it writes anything. `(clarify / requirements liaison)`
- **It lists what you left unsaid** — Every decision your goal didn't make gets laid out and ranked; the risky
  ones stop the build. `(assumption gate)`
- **It won't build on a hunch** — If something important is still unconfirmed, it refuses, instead of guessing
  and hoping. `(input-first hard-stop)`
- ★ **If your spec and tests disagree, it stops** — A contradiction halts the build and makes you fix it, not
  paper over it. `(reconcile-fails-closed)`
- **Every call gets written down** — What you decided, and why, lands in a file you can point back to.
  `(<plan>.decisions.md)`
- ★ **Someone watches for 'not what I meant'** — A stand-in for you sits in on the whole run and can veto a
  finished build that drifted from what you wanted. `(THE ADVOCATE)`

**Payoff:** *It drags every quiet guess into the open before it builds — and someone whose only job is what you
meant can hit the brakes.*

**Proof ⏳ (needs a live model)** — claim: *"The interviewer and your stand-in think out loud — with a real
model."* The decision-making logic is unit-tested and passing; the live back-and-forth (the assumption auditor
and the Advocate) needs the analyst model running, which isn't up in the demo sandbox. Show it live later.

---

### CHAPTER 4 — "The death spiral"
**Problem — "When it's stuck, it just tries harder."**
*It fails, so it retries. Fails again, so you reach for a bigger, pricier model. Then you give up and patch the
output by hand — and now nobody knows what's real. None of it fixed the actual problem: the instructions were
fuzzy.*
Pain chips: `retry, retry` · `bigger model` · `patch it by hand`

**Arsenal — problem node: "Failures snowball instead of teaching"** (5 angles)
- ★ **It fixes the recipe, not the dish** — When a build fails, it rewrites the *instructions*, then the same
  cheap model tries again. `(THE HEALER / spec repair loop)`
- **No panic-upgrade to a bigger AI** — It doesn't throw money at a smarter model; it makes the task clearer.
  `(no-escalation doctrine)`
- **A bug fix has to catch the bug** — Your fix has to fail on the *old* code first. If it passes there, it
  never caught anything. `(regression-proof)`
- **Every failure is kept as evidence** — The exact thing that broke gets saved, so the next attempt learns.
  `(failure-as-asset)`
- **Three strikes, it calls you** — If it can't crack something in three honest tries, it stops grinding and
  asks a human. `(Rule-of-Three)`

**Payoff:** *A failure doesn't mean 'try harder.' It means 'the instructions weren't clear' — so it fixes those,
and moves on.*

**Proof ⏳ (needs a live model)** — the self-repair loop (the Healer) rewrites specs with a model; the
'a-fix-must-catch-the-bug' check *only exists inside a real build*. Both need the local model up. Flag honestly.

---

### CHAPTER 5 — "No trail, no leash, no cleanup"
**Problem — "No paper trail, running loose, leaving a mess."**
*Who wrote this line — which model, from what instructions, and what did it ever pass? Nobody knows. Meanwhile
it's running code on your machine, and last month's dead files are still lying around for the next tool to trip
over.*
Pain chips: `no history` · `runs on your box` · `util_final_OLD.py`

**Arsenal — problem node: "You can't audit it, trust it, or clean up after it"** (8 angles)
- **Every line has a receipt** — Trace any function back to the exact request, test, model, and version.
  `(provenance chain)`
- **Point to the test behind any rule** — 'Where's this handled?' → one command shows the requirement and the
  test that proves it. `(traceability / lathe trace)`
- ★ **Every run signs its own record** — Who did what, what it cost, what passed, sealed with a fingerprint so
  it can't be quietly edited. `(THE REPORTER / run manifest)`
- **It reads a plan without running it** — A booby-trapped plan gets rejected as plain data, before a single
  line executes. `(plan validator)`
- **Sketchy code runs in a padded room** — Model code runs boxed-in, no network, read-only. `(sandbox + tiers)`
- **It only touches what it made** — It won't overwrite your hand-written files, and it can't call out to
  strange URLs. `(provenance markers + SSRF guard)`
- **One real file per job, always** — Ask 'which file is live?' and get a straight answer. `(canonical + whatis)`
- **The build fails if junk piles up** — Leftover backups and duplicates stop the build until it's clean.
  `(stale/dup gate)`

**Payoff:** *Every run leaves a signed receipt, risky code never runs loose, and the folder stays clean on its
own.*

**Proof ✅** — claim: *"Every run signs itself — and a booby-trapped plan gets bounced."*
```
$ cat docs/ce/…manifest.json
  outcome: pass    signed: sha256:5477c7ba…

>>> is_valid_plan(booby_trapped_plan)
  { ok: False, "plans must be data, not a program" }
```
Verdict: *Signed receipt written · the hostile plan was refused before it could run.*

---

### CHAPTER 6 — "One model, one trick"
**Problem — "One pricey model — and all it does is type code."**
*Everything goes to one expensive model in someone else's cloud, on their terms. And it only writes code.
Reviews, bug fixes, refactors, the whole process around the code? You're on your own.*
Pain chips: `one vendor` · `$$$ a token` · `only writes code`

**Arsenal — problem node: "One brain, one trick, their servers"** (6 angles)
- **Smart model plans, cheap model types** — The expensive brain writes the spec once; a small local model does
  the grunt work. `(division of labour)`
- ★ **A whole bench of specialists** — 143 expert reviewers on call; it picks the right ones and learns who
  actually finds bugs. `(persona market)`
- ★ **It's not just a code writer** — Reviews, bug-fixes, enhancements, doc checks, a full build process; whole
  jobs, not snippets. `(workflow modes)`
- **Use whatever model you like** — Plug in any model at either end; not married to one vendor. `(BYO brain)`
- **Runs on your laptop, on your terms** — Local by default: private, no per-token bill. `(local-first)`
- **Fits where you already work** — Your command line, inside your own code, or as a tool in your AI editor.
  `(CLI / embedded / MCP)`

**Payoff:** *The right brain for each job — most of them on your own machine — and it does a lot more than write
code.*

**Proof ✅** — claim: *"143 experts and 20 kinds of job — real, not marketing."*
```
$ how many experts, really?
  143 reviewers in the catalog

$ lathe flow
  bug-fix · code-review · doc-review · enhancement · sdlc · new-project …
  20 named jobs — not one of them is "just write code"
```
Verdict: *Counted straight from the real catalog and the real command.*

---

### CLOSER
- Eyebrow: *so, the whole thing*
- Headline: **"No magic. Just a lot of nets."**
- Body: *One check can miss. That's the whole point of doing it many ways: reproduce it, test it for real, keep
  it honest about what it assumed, make failures teach it, sign every run, bring in the experts. Miss one net —
  the next one catches it.*
- Final line: **"That's AI you can depend on — it does the right thing, and it can prove it, before it ships."**

---

## 7. Existing assets to reuse (don't recreate the look — extend it)

Under `docs/infographics/` — a finished, on-brand set (warm flat-vector, the palette above). Reference them for
style, iconography, and tone:
- `19_method_overview.png` — the whole method in one picture (lead image)
- `01_build_loop.png`, `02_division_of_labor.png` — the loop and the analyst/implementer split
- `15_determinism_two_claims.png` — the reproducibility split
- `13_methodology_enforced.png` — the eight-gate rack (just updated: **eight** gates incl. spec-lint)
- `10_safety_spine.png` — the safety layers
- `18_assumption_gate.png` — the assumption gate (writes `<plan>.decisions.md`)
- `14_provenance_chain.png`, `12_works_with_your_stack.png`, `06_loop_that_learns.png`, `11_discipline_enforced.png`
- `20_honest_ledger.png`, `21_try_it_once.png` — the newest two (verified/bounded/not-proven ledger; the 5-min CTA)

Also: **`docs/INTRODUCING_LATHE.md`** — the long-form article (Fable's voice) is the closest existing thing to
the target register; mine it for phrasing. **`docs/infographics/NANO_BANANA_PROMPTS.md`** — the image prompt
library + palette/style guide. **`LATHE_CAPABILITIES.md`** / **`docs/CAPABILITY_MAP.md`** — the authoritative
capability inventory (every mechanism above is grounded there).

---

## 8. Suggested components (design-system framing)

- **ProblemCard** — eyebrow ("The problem"), big headline, one human paragraph, a row of red "pain chips."
- **ArsenalBoard** — a red **problem node** + a responsive grid of **MechanismCards** converging on it +
  a sage **PayoffBar**. Mechanism card = human title + one-line gloss (+ optional ★ for "newer/lesser-known").
- **ProofCard** — a realistic **terminal card** (dark, dots, `$` prompt, green success lines) + a green
  **verdict pill**; amber variant for "needs a live model."
- **TerminalBar / chrome** — the whole deck sits in a "build console" frame (three dots + `lathe` title +
  slide number) to reinforce "this is a build tool."
- **Controls** — Prev / Play / Next, a chapter menu, progress bar, light-dark toggle. Keyboard: arrows, space, M.

---

## 9. Honesty rules (non-negotiable — it's the brand)

- **A claim isn't real until it's backed by a runnable example.** Every "fix" chapter ends in a proof screen.
- Where a proof needs a live model (Chapters 3 & 4, plus regression-proof and live review), **say so** in amber
  — never fake a green result. The captured ✅ outputs in §6 are real (run against the tool this session).
- Some capabilities are **opt-in** (turned on with `LATHE_STRICT=1`) or **built-but-not-yet-autonomous**. The
  deck can present them as real (they exist) without implying they're all on by default. If the user later wants
  status badges (✅ on / ⚙️ opt-in / 🔌 available), the catalog has the exact status per item.

---

## 10. Format & constraints

- **Self-contained HTML/CSS/JS artifact** (renders on claude.ai). **No external assets** — CSP blocks CDNs;
  inline all CSS/JS, embed any image/font as a data-URI.
- **Responsive**; the slide area must **grow to fit content** (never clip) and scroll internally on short
  viewports — a fixed 16:9 box clipped earlier drafts on mobile.
- **Both light and dark themes**, token-driven.
- **Verify it renders headlessly before shipping** (no console errors, no clipping) — earlier drafts shipped
  broken because this step was skipped.

---

## 11. Lessons from the drafts (so we don't repeat them)

1. **Voice first.** The biggest failure was jargon. If a slide sounds like documentation, it's wrong.
2. **One problem, many angles** beats one-problem-one-solution. AI fails in scattered ways; the story must show
   defense-in-depth. This is also the thesis, made visual.
3. **Don't miss the marquee capabilities:** the **Advocate**, the **Healer**, the **Reporter**, **review-as-a-
   mode** (not just codegen), the **persona market**. Early drafts omitted these.
4. **Prove it.** Real command + real output per chapter. Flag the model-dependent ones honestly.
5. **Tighten.** Six big problems, not fifteen small ones. Dense with value, not repetitive.

---

## 12. Open questions for the user / designer

- **Name on the face:** "Deterministic AI" (spelled out) vs **AID** vs **D·AI** vs just "AI you can depend on"?
- **Format:** interactive web deck (recommended) — or also a **linear video/storyboard** version for social?
- **Depth:** should the marquee mechanisms (the pin, the gate, the Advocate, the persona bench) get their own
  deeper mini-animation, beyond the arsenal card?
- **Proofs:** stand up the local model to capture the 4 pending (⏳) proofs for real, before finalizing?
```
```
```

_Grounding: every mechanism and status in this brief is drawn from `LATHE_CAPABILITIES.md` and
`docs/CAPABILITY_MAP.md`; the ✅ proof outputs were captured by running the tool this session
(`lathe verify`, `review_tests/test_mutation_score.py`, the run manifest, `is_valid_plan`, the persona catalog,
`lathe flow`)._
