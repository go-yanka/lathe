# Nano Banana prompt library — Lathe infographics

*Authored by Fable. Every prompt is grounded in `docs/CAPABILITY_MAP.md`; status badges (● live / ○
available) follow the ✅/🔌 in that map so no graphic implies an unshipped capability is autonomous.
Prompts 1–5 are already generated and final (files noted); 6–11 are new.*

## Shared style guide (paste at the top of any prompt, or reference the first generated image)
> Clean, modern flat-vector infographic. Soft off-white (#F4EEE1) background, rounded cards with soft
> shadows, thick consistent line weight, a warm palette (deep indigo-brown ink #3D2B22, teal #7EA8A1,
> coral #E4986B, sage #8DB26A, muted amber, soft grey), friendly outline icons each in a soft colored
> circle, large legible sans-serif, generous whitespace, minimal text, no paragraphs, no misspellings.
> Match the style of the reference image exactly.

**Workflow tips:** generate #1 first, then feed it back as a reference ("match this style/palette/font")
for the rest. Keep labels short — Nano Banana degrades past ~15 text elements; for anything denser (the
full capability map) use the hand-rendered SVG instead (`00_capability_map.svg`). After each generation,
eyeball the text and re-run with "fix the text to read exactly: …" for any garbled label.

---

## GENERATED & FINAL (kept for reference)
1. `01_build_loop.png` — the pipeline GOAL→ANALYST→IMPLEMENTER→GATE→PIN + FAIL loop. ✅
2. `02_division_of_labor.png` — analyst vs implementer, model-agnostic ribbon. ✅
3. `03_strengths.png` — 5 strengths (test-gated·pinned·no-hand-edits·local-or-any·provenance). ✅
4. `04_determinism.png` — pin+reuse = same code (first-build lane vs rebuild lane). ✅
5. `05_capability_map_poster.png` — 9-bucket capability poster. ✅  (exhaustive version: `00_capability_map.svg`)

---

## NEW PROMPTS

### 6 — "The loop that learns" (the feedback loop; 16:9)
```
[style guide]. Title: "The loop that learns". Subtitle: "when a build fails, the SPEC gets sharper — not
the model bigger". Center on a big clockwise CLOSED LOOP spanning two tinted zones: LEFT "THINKING HARNESS
(analyst)" with a glowing brain icon "writes spec + tests"; RIGHT "IMPLEMENTATION HARNESS (engine + gates)"
with a chip icon "local model builds" and a shield-check "gate runs the tests". Arrows clockwise: analyst
—(spec+tests)→ local model builds —→ GATE. From GATE two arrows: a GREEN one OUT of the loop "PASS → pin +
ship" (to a padlock-# icon), and a RED one curving BACK to the brain "FAIL: bank the failing test →" then
"analyst sharpens the SPEC". Centered accent-box callout: "No escalation. The thinking fixes the spec; the
cheap model still does the build." Footer ribbon: "every failure is banked as evidence for a sharper spec".
```
*Status note: all ✅ (shipped). Footer states the mechanism, not the unproven "fewer tries over time" outcome.*

### 7 — "A tree an AI can't get lost in" (cleanliness; 16:9)
```
[style guide]. Title: "A tree an AI can't get lost in". Two side-by-side panels. LEFT panel, header
"WITHOUT" in muted red: a messy file-tree icon showing "util.py", "util_v2.py", "util_final.py",
"util_OLD.py"; caption "which one is real? the model guesses — and patches the wrong copy". RIGHT panel,
header "WITH LATHE" in sage green: a clean tree with a single "util.py" carrying a green check and a small
"canonical" tag; three checkmarked lines below: "one live file per capability", "no stale / duplicate
files (build fails if they appear)", "`whatis` tells you which is real". Footer ribbon: "the gate keeps the
tree honest — so an agent always edits the right thing".
```
*Status: ✅ (six standing gates + registry).*

### 8 — "Cheap context: read the map, not the files" (token efficiency; 16:9)
```
[style guide]. Title: "Read the map, not the files". Two-column comparison. LEFT, header "DUMP THE FILES"
muted red: a huge stack-of-documents icon with a big red token counter "~40,000 tokens" and caption "send
whole files for context". RIGHT, header "SEND THE STRUCTURE" sage green: a compact outline/tree-of-symbols
icon (function names + signatures) with a small green counter "~2,000 tokens" and caption "ctags repo-map:
names, kinds, signatures". Below, a second small row: "skeleton-fill: model writes only the blank" and
"skeleton-complete: 0 tokens — no model call". Small ○ (available) badges on each item. Footer ribbon:
"structure is 20× cheaper than source — and enough to reason about the code".
```
*Status: ○ available (repo-map/skeleton features are built, not on the autonomous path — badge them ○).
Token numbers are illustrative; render them as "~" ranges, not exact claims.*

### 9 — "Three ways to run it" (distribution; 16:9)
```
[style guide]. Title: "Three ways to run Lathe". Three equal columns, each a card with an icon, a bold
label, one line of detail, and a status dot. Col 1 ● "STANDALONE" terminal icon "its own CLI + chat REPL".
Col 2 ○ "INSIDE YOUR AGENT" puzzle-piece/MCP icon "an MCP tool in Claude Code, Cursor, Copilot". Col 3 ●
"EMBEDDED" gear/import icon "import the engine, or drive it from any agent". Below the three, a slim
two-row strip: "ANALYST: Claude · any OpenAI-compatible · or a human" and "IMPLEMENTER: local by default ·
Ollama / llama.cpp / vLLM · or any model". Small legend: "● live  ○ available". Footer ribbon:
"pluggable at both ends — bring your own models".
```
*Status: standalone ● , MCP ○ , embedded ● . Honest badges matter here — don't render MCP as ●.*

### 10 — "The safety spine" (security; 16:9)
```
[style guide]. Title: "Why running model-written code here is safe". A vertical stack of 3 defense layers,
each a wide rounded bar with an icon and a short label+subtext, like a layered shield: Layer 1 (top)
"PLAN VALIDATOR" clipboard-lock icon — "a plan is data, not a program: allowlisted imports, no dunders,
pure-literal fields; a malicious plan is refused before anything runs". Layer 2 "SANDBOX" shield icon —
"code runs isolated; the pass/fail verdict is nonce-framed so a test can't fake a pass". Layer 3
"ISOLATION TIERS" nested-boxes icon — "subprocess → docker → docker-over-SSH: network-less, read-only,
fail-closed". Small side badges: "SSRF guard · provenance markers · MCP input guards". Footer ribbon: "the
one honest floor: a plan you build is code you run — so untrusted plans run in the container tier".
```
*Status: ● (validator, sandbox, tiers, guards all shipped). The footer keeps SECURITY.md's honest caveat.*

### 11 — "The discipline you already believe in — enforced" (the methodology hook) — CORRECTED
*Original framing (Cleanroom / "discipline died" / "developers never test their own code") was killed by a
Fable fact-check — `GRAPHIC11_FACTCHECK.md`: nobody knows Cleanroom, the "never test own code" claim is
false, and TDD/CI/lockfiles didn't die. This is the corrected, relatable version. 16:9.*
```
[style guide]. Title: "The discipline you already believe in — enforced". Subtitle: "test-first · never
merge red · locked builds · don't hand-patch the compiler". A 2-column "you know this / Lathe enforces it"
comparison styled as clean cards (NOT a spreadsheet). Four rows, each a small icon on the far left:
  Row 1: "TEST-FIRST"        — icon: a checklist.
  Row 2: "NEVER MERGE RED"   — icon: a red/green build light.
  Row 3: "LOCKED BUILDS"     — icon: a padlock.
  Row 4: "DON'T HAND-PATCH THE COMPILER" — icon: a compiler/gear.
Column 1 header "YOU ALREADY DO THIS" (small caption "TDD · CI · lockfiles · the compiler contract"): each
cell a check, plus a small faded note "…until Friday" or "…when there's time".
Column 2 header "LATHE ENFORCES IT" in sage green: each cell a green check with a tiny robot/lock, reading
respectively "analyst writes the test first", "the gate refuses a red build", "content-hash pins the build",
"wrong code = fix the spec, rebuild".
Footer ribbon: "good practice runs on willpower — and willpower loses to deadlines. move it onto the machine."
```
*Status: ● (maps to shipped gates/loop/pins). Positioning centerpiece from `PRODUCT_STRATEGY.md` §3.
Every claim here is a practice a working dev used in 2000–2020 — no obscure history, no false universal
claim.*

### 12 — "Works with the stack you already have" (compatibility / interop; 16:9) — GENERATED & FINAL
*File: `12_works_with_your_stack.png`. The adoption-forward interop story — pluggable at BOTH ends × runs
anywhere. Stronger than #9 for "it fits what I already run." **Honesty checks that passed on the render:**
MCP badged ○ (available, NOT ●); Hermes framed as an EXAMPLE open model (Hermes · Qwen · Llama), not a
named Lathe integration — the code names only Ollama / llama.cpp / vLLM / LM Studio + any OpenAI-compatible
endpoint.*
```
[style guide]. Title: "Works with the stack you already have". Subtitle: "pluggable at both ends · runs
anywhere · bring your own models". Center: a rounded teal core box "LATHE" with "spec → gate → pin" under
it; an arrow IN from the left, OUT to the right. LEFT, header "THINKING END" + brain icon, a card:
"Claude" / "any OpenAI-compatible endpoint" / "or a human"; caption "the analyst writes spec + tests".
RIGHT, header "BUILDING END" + chip icon, a card: "local open models — Hermes · Qwen · Llama" / "via
Ollama · llama.cpp · vLLM · LM Studio" / "or Claude"; caption "the implementer writes the code". BOTTOM:
three equal cards "RUN IT" each with icon + bold label + one detail + status dot — ● "STANDALONE" "its own
CLI + chat REPL"; ○ "INSIDE YOUR AGENT" "MCP tool in Claude Code, Cursor, Copilot"; ● "EMBEDDED" "import
the engine". Legend "● live  ○ available". Footer ribbon: "bring your own models at both ends — Lathe is
the gate in the middle".
```
*Status: standalone ● , MCP ○ , embedded ● . Hermes = illustrative open model, not a special connector.*

### 13 — "The methodology, enforced by the build" (the enforcement stack; 16:9) — GENERATED & FINAL
*File: `13_methodology_enforced.png`. The payoff to #11's hook. The most-defensible graphic in the set —
**every gate is a claim the review reproduced green** (traceability 12/12, regression-proof 8/8,
mutation-score 9/9 + the v2.2.1 E1–E4 fixes). Only ships honestly WITH the bottom band: opt-in / bounded
tripwire (not exhaustive) / per-function (not whole-system). All three clauses verified present on the
render. Do NOT drop the band or the word "declared" in gate 1.*
```
[style guide]. Title: "The methodology, enforced by the build". Subtitle: "three gates a change must pass
before it can ship — the model can't skip them". Center: a left-to-right flow. Far left a document icon
"spec + tests + code" → through THREE tall gate cards (each icon + bold name + one line + a small red "✗
refused" tag): Gate 1 "TRACEABILITY" (link) "every declared requirement maps to a named test"; Gate 2
"REGRESSION-PROOF" (bug/shield) "a fix must ship a test that fails on the old code"; Gate 3 "MUTATION-SCORE"
(target) "the suite must kill the code's mutants" → a green padlock-hash "PINNED — accepted". Above the
gates a sage-green banner brace "LATHE_STRICT = 1 · forces all three, for every change". Bottom muted band:
"⚙️ opt-in, off by default · mutation-score is a bounded tripwire for vacuous tests, not exhaustive
coverage · gates each function, not your whole system". Footer ribbon: "the kind and thoroughness of
testing come from the process — not the model's discretion".
```
*Status: all ✅ verified (#1/#2/#3 reproduced). #5 kind-of-test and #6 glue still open → the "each function,
not your whole system" clause is mandatory, not optional.*

### 14 — "Provenance, by construction" (the compliance / audit chain; 16:9) — GENERATED & FINAL
*File: `14_provenance_chain.png`. The paying-niche / audit story (PRODUCT_STRATEGY §6). Mostly verified: the
pin is `sha256(name+prompt+tests+model)` (spec+tests+model+hash bound by construction) and `lathe trace`
emits criterion→test→pin→model. **Two honest scopes are mandatory in the band** and were verified present on
the render: (a) the REQUIREMENT link exists only when CRITERIA are declared (traceability is opt-in);
(b) the sandbox verdict is proven by the pin existing (only passing code pins), NOT a separate cryptographic
attestation. Don't drop either — without them the compliance claim over-reads.*
```
[style guide]. Title: "Provenance, by construction". Subtitle: "every function carries its own record —
built in, not assembled after". Center: a left-to-right chain of SIX linked cards (icon + bold label + one
sub-line, chain-link connectors): (1) clipboard "REQUIREMENT" "declared criterion"; (2) document "SPEC"
"the analyst's prompt"; (3) checklist "TESTS" "the asserts it passed"; (4) shield-check "GATE" "only
passing code pins"; (5) chip "MODEL" "which model wrote it"; (6) padlock-hash "HASH" "content-hash pin"
(emphasized sage green). Wide callout below: "one tamper-evident record per function — machine-generated at
build time". Bottom muted band: "requirement link when criteria are declared · the verdict is proven by the
pin (only passing code pins), not a separate attestation". Footer ribbon: "traceability isn't a report you
assemble — it's a property of the artifact".
```
*Status: pin binding (spec+tests+model+hash) ✅ verified; `lathe trace` chain ✅ verified. Scopes: requirement
needs declared criteria; verdict is proven-by-pin, not stored attestation — both in the band, mandatory.*

### 15 — "Determinism you can prove" (the two-claims split; 16:9) — GENERATED & FINAL
*File: `15_determinism_two_claims.png`. Sharpens #04. The trust move is showing the "NOT CLAIMED" lane
proudly. Lane A (pinned = byte-identical, 0 tokens) reproduced by the review; Lane B (regeneration
byte-different but green) is the honest counterpart, measured in `REPRODUCIBILITY.md`. Grounded in that file
verbatim.*
```
[style guide]. Title: "Determinism you can prove". Subtitle: "the rebuild is deterministic — the model
isn't". Two side-by-side lanes. LEFT (sage-green header "GUARANTEED — pinned rebuild", padlock+replay icon):
three green-checked lines — "same plan + same pins", "0 model calls · 0 tokens", "byte-identical output —
even on a clean checkout". RIGHT (muted-amber header "NOT CLAIMED — regeneration", dice/shuffle icon): three
lines — "evict the cache → the model runs again", "byte-DIFFERENT code", "…but still passes the same gate
(green)". Center medallion between the lanes: "determinism is a property of the BUILD — pin + replay — not
the model". Footer ribbon: "a lockfile for AI code".
```
*Status: Lane A ✅ reproduced (0 tokens, byte-identical); Lane B stated as NOT guaranteed — the honesty is
the point. Keep the right lane; never soften it.*

### 16 — "A library of experts, on tap" (the persona market; 16:9) — GENERATED & FINAL (AUTO-FETCHED = ○)
*File: `16_expert_library.png`. Badge split verified on the render: AUTO-SELECTED ● · AUTO-FETCHED ○ ·
LICENSE-GATED ● · EMPIRICALLY RATED ○ (the two ○ are the pieces the reviewer couldn't reproduce
end-to-end).*
*The persona/agent market. Honesty badges (per the review's reproduced-by-me standard): AUTO-SELECTED ● and
LICENSE-GATED ● (verified); AUTO-FETCHED ○ (shipped + maintainer-proven-live, but the live GitHub pull is
sandbox-blocked for the reviewer, so conservatively ○); EMPIRICALLY RATED ○ (tool present, manual step).
143 catalog count verified.*
```
[style guide]. Title: "A library of experts, on tap". Subtitle: "the right reviewer for the code — picked,
not configured". Center-left: a large sage-green circle with big number "143" and under it "expert review
personas". Right: a vertical list of four small cards, each icon + short label + one line + a status dot —
● "AUTO-SELECTED" "the decider matches personas to the code's domain"; ○ "AUTO-FETCHED" "pulls a missing
expert from the catalog on demand"; ● "LICENSE-GATED" "permissive licenses only — refuses unknown-license
sources"; ○ "EMPIRICALLY RATED" "field-probe + an independent judge score each expert". Legend "● live  ○
available". Footer ribbon: "a growing catalog — the decider brings the expert to the code".
```
*Status: 143 ● , auto-select ● , license-gate ● , auto-fetch ○ (conservative), ratings ○ .*

---

## Recommended order to generate
11 (the hook — leads any launch) → 6 (the loop — most-requested strength) → 7 (clean tree) → 10 (safety) →
9 (distribution) → 8 (token efficiency). Then you have: hook → how it works (existing #1) → who does it
(#2) → the loop (#6) → determinism (#4) → clean tree (#7) → safety (#10) → run anywhere (#9) → tokens (#8)
→ strengths recap (#3) → full map (SVG). A complete visual narrative for a launch page or deck.

## Honesty rules (carried from the review standard)
Every graphic shows real ● / ○ status; never render a ○ capability as shipped-autonomous; frame local-model
economics as default + invitation-to-test (not proven); omit anything not yet wired (e.g. decider
auto-fetch, review §15 D7); illustrative numbers get "~" and are labeled illustrative.
