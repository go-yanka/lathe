# Lathe — Capability Map (bucketed + prioritized)

An exhaustive inventory of Lathe's capabilities (**refreshed to v2.6.2**), grouped into buckets and
prioritized within each.
**Provenance (two separate channels):** the capability *list* was drawn from the code plus
`LATHE_CAPABILITIES.md` / `LATHE_COMMANDS.md`; every *status label* below was **verified against the
executable source** (`engine_v2.py`, `run_gates.py`, `lathe.py`, `lathe_mcp.py`, `tools/*`) — the code is the
oracle, not the sibling docs. Status legend: **✅ wired** (on the autonomous path) · **🔌 available**
(built/tested, not autonomous) · **🧠 analyst** (premium/human front-end) · **⚙️ opt-in gate** (built +
reproduced, off by default / STRICT-forced — no autonomous-path change unless enabled).
**v2.6.1 refresh note:** all **6 methodology mechanisms** ship — regression-proof (#1), traceability (#2),
mutation-score (#3), test-ack (#4), required test-kind (#5), gate-the-glue (#6) — plus the **assumption
gate**, which `LATHE_STRICT=1` composes as **seven gates** (＋ the lint stub-block it also flips; traceability
is enforced as a plan-gap requirement rather than an env toggle — see Bucket C). **Honest count:** #4
(test-ack) is a *partial oracle* — a human re-read of the test set, not a second independent author — so it's
"6 shipped, #4 partial," never "6/6 done." There are now two "no silent guessing" **front-ends** (`lathe
clarify` + the adversarial `assumption-auditor`). Every mechanism was **independently reproduced** by the
review (see `METHODOLOGY_ENFORCEMENT_VALIDATION.md`; the reproduction harness is the review's own — the
executable, not the label, is authoritative). The gates are **opt-in / STRICT-forced** (default off), so they
carry a ⚙️ marker: *gated capability, off by default, no autonomous-path behavior change unless enabled*.
(Prior refresh reached only v2.2.0 / 3-of-6; superseded.)
Priority: **P0** = flagship differentiator · **P1** = important/core · **P2** = supporting. **The priority axis
(P0/P1/P2) is independent of the status axis (✅/🔌/🧠/⚙️)** — a P0 flagship can still be 🔌 (built but not yet on
the autonomous path); the two must be read together, not conflated.

---

## Bucket A — The build engine (the "compiler")
- **P0** Plan-driven build — a plan (data) is compiled into code; no LLM in the driver. ✅
- **P0** Per-**function** granularity — spec+tests as the unit of generation (not feature-level). ✅
- **P1** Best-of-N generation with temperature ramp. ✅
- **P1** STRICT validation gate — exec `HEADER+code` in a clean namespace, run each assert. ✅
- **P1** Module assembly — `HEADER + funcs + GLUE` → `<MODULE_NAME>.py` on all-green. ✅
- **P1** Implementer routing — `openai:local` / ollama / `claude`, per-call. ✅
- **P2** Per-function model/level selection (engine sticks, no silent swap). 🔌
- **P2** Integration test — assembled module must pass `INTEGRATION` as a whole. 🔌
- **P2** Artifact / whole-file output (UI/API/config) from prompt+tests. 🔌
- **P2** Analyst-directed retirement (`RETIRE` → `_archive/`). 🔌

## Bucket B — Reproducibility & determinism (THE headline differentiator)
- **P0** Content-hash pinning — `sha256(name+prompt+tests+model)` → byte-identical rebuilds. ✅
- **P0** Rebuild reuses the pin with **zero model calls** — determinism by reuse, not by taming the model. ✅
- **P1** Failure-as-asset — failed candidate + exact failing test banked (`_fn_fails/`) for spec repair. ✅
- **P2** timeout ≠ fail — a gate timeout is flagged flaky, not banked as a spec failure. ✅

## Bucket C — Verification & quality gates (the acceptance layer)
- **P0** Hard test gate — code is **accepted only if its tests pass** (acceptance, not a repair loop). ✅
- **P0** Isolated sandbox with an **unforgeable nonce verdict** (subprocess / docker / docker-ssh tiers). ✅
- **P0** Test-quality linter — **mutation probe** (single-stub): flags tests a trivial stub could satisfy. 🔌
- **P0** **Mutation-*score* threshold** (methodology #3, v2.2.0) — deterministic AST mutants of accepted code
  (arith/compare/int-const) must be killed at ≥ `LATHE_MUTATION_SCORE`; a suite that can't discriminate the
  code from its mutants is BLOCKED before pinning. Fails **closed** on malformed inputs. ⚙️ (reproduced 9/9 +
  17/17 pure logic)
- **P0** **Requirement→test traceability, enforced** (methodology #2, v2.1.5) — a plan's declared `CRITERIA`
  must each map to ≥1 named test; the validator refuses unmapped criteria / dangling refs / dup ids; `lathe
  trace` emits the criterion→test→pin→model matrix (the compliance artifact). ⚙️ (reproduced 12/12)
- **P0** **Regression-proof** (methodology #1, v2.1.6; generalized to enhancements under STRICT v2.1.7) —
  `LATHE_REGRESSION_PROOF=1`: a changed function whose new tests all pass on the OLD accepted impl is REFUSED
  before a token is spent (no reproducing test = no build). ⚙️ (reproduced 8/8 + 6/6 pure logic)
- **P0** **Test-ack gate** (methodology #4-partial, v2.1.4) — `LATHE_TEST_ACK=1` / `lathe ack`: refuses to
  build until a human has acknowledged this exact test set; any rewrite (incl. repair loop) re-forces it. ⚙️
- **P0** **Required test-KIND per contract** (methodology #5, v2.2.4) — `LATHE_TEST_KIND=1`: a unit whose
  tests lack its declared `kinds` (property / edge / roundtrip / error) is REFUSED before generation;
  detected structurally, no model call. Property tests are a requirable kind. ⚙️ (reproduced ALL PASS)
  *Honest limit: kind-detection is a **presence heuristic** (substring match over the test text), so a
  comment mentioning "invalid"/"[]"/"none" can satisfy it — the mutation-score gate is the real rigor;
  test-kind is a "did you even write an edge test" tripwire, not a guarantee the edge test is meaningful.*
- **P0** **Gate-the-glue** (methodology #6, v2.2.3) — `LATHE_GATE_GLUE=1`: substantive hand-written `GLUE`
  must be exercised by an `INTEGRATION` test or the build is refused. Closes "function, not anything": under
  STRICT, no *code* ships untested. ⚙️ (reproduced ALL PASS)
- **P0** **Assumption gate** (v2.5.0; **resolve-not-rubber-stamp v2.6.0/v2.6.1**) — `LATHE_ASSUMPTION_GATE=1`
  / `lathe assume`: an adversarial `assumption-auditor` re-reads the spec against the goal and emits a
  materiality-ranked ledger of the decisions the goal never specified; the engine REFUSES to build while any
  HIGH assumption is unresolved. **An empty auto-audit (0 surfaced) is flagged ADVISORY, not a clean pass**
  (v2.6.2, in the trail + console + engine) — a model self-audit that collapses its own ledger can't launder
  as human review; and engine-side enforcement now **fails closed** (only genuine gate-absent import errors
  opt out). `--resolve` throws each blocker back for an **explicit per-item decision** —
  accept as the real intent, pick an offered `[options: …]`, or type what you actually want; **skipping stays
  blocking** (fail-safe). Every decision is recorded (with its method) in a **committed `<plan>.decisions.md`
  audit trail** — a resolved assumption becomes a *stated decision*, not a silent guess. `--yes` blanket-accept
  was removed; `--accept-all` is an explicit opt-in, logged as "accepted in bulk." Spec change re-opens via
  digest. Scrutiny user-governed (`all›high+med›high›off`). ⚙️ (reproduced ALL PASS incl. per-item resolve,
  skip-stays-blocking, bulk-recorded-honestly, spec-change re-open)
- **P0** **STRICT / SDLC umbrella** (v2.1.7 → **seven gates** by v2.5.0, assumption gate *enforcing* as of
  v2.6.1) — `LATHE_STRICT=1` composes traceability + test-ack + regression-proof + mutation-score + test-kind
  + gate-glue + assumption-gate — the **seven gates** — **plus the lint stub-block** (`LATHE_LINT_SPEC=block`),
  i.e. eight blocking checks in all; traceability is enforced as a required-`CRITERIA` plan-gap, the rest via
  env toggles (`strict_mode.py`). Forces all development through every proof; explicit env vars still win. ⚙️
  (reproduced 7/7 + 8/8 pure logic). *Note: "seven gates by v2.5.0" counts the assumption gate as composed,
  but at v2.5.0 it was still a weak ack; per-item enforcement (`--resolve`, no blanket-accept) is v2.6.0/v2.6.1.*
- **P1** Six standing gates: stale · resource-dups · registry · pristine · real-bug-lint · docs-drift. ✅
- **P1** Functional/behavioral gate — live headless browser (Playwright) checks the real DOM. 🔌
- **P1** Structural gate — asserts against generated artifact `content`. 🔌
- **P2** H3–H6 product gates — visual-regression · performance · security(SAST+SSRF) · accessibility(axe). 🔌
- **P2** Data-quality primitives — distribution-anomaly · dangling-refs · incomplete-records. 🔌
- **P2** Cassette record/replay — deterministic offline LLM-pipeline e2e gates. 🔌
- **P2** road_ready DoD — fresh-subprocess import → boot → HTTP health → live smoke. 🔌

## Bucket D — The thinking layer & feedback loops (the "agentic loop")
- **P0** **Step 0 — requirements liaison** (`lathe clarify`, v2.3.0; selectable options v2.4.0) — interrogates
  a vague goal for ambiguity *before* the harness thinks: fewest sharp questions (inputs/outputs/success/edge/
  non-goals) with pick-from options, writes `CLARIFIED_GOAL.md` with **testable acceptance criteria**. A goal
  already stating inputs+outputs passes through. Step 0 of `sdlc`. ✅ (reproduced ALL PASS + 8/8 logic)
- **P0** **Assumption auditor front-end** (`lathe assume`, v2.5.0) — the adversarial spec-audit twin of
  clarify: surfaces the *silent* decisions a spec made that the goal never specified, materiality-ranked;
  advisory at `clarify`, enforced pre-build (see the assumption gate in Bucket C). ✅ (reproduced ALL PASS)
- **P0** Repair loop — on gate failure the **analyst rewrites the SPEC** from the banked failing test, then
  retries (implementation harness → thinking harness feedback). ✅
- **P0** No-escalation doctrine — a failure sharpens the spec; it never summons a bigger model to build;
  Rule-of-Three escalates to a human after 3 tries. ✅
- **P1** Analyst plan authoring — premium model (or human) writes spec+tests; pluggable. 🧠
- **P1** CE review personas — multi-lens (correctness/adversarial/security/data/reliability/perf/api/
  maintainability/testing/ui), vendored, injected as real reviewer lenses. 🧠
- **P1** Review decider — `review auto` auto-selects personas fitting the code's domain, and (v2.1.4, D7
  fixed) **auto-fetches a missing expert** from the catalog when the decider needs one no longer vendored. ✅
- **P1** Planner lens injection — a goal auto-injects expert lenses into the analyst's thinking prompt. ✅
- **P1** On-demand persona catalog — license-gated fetch of expert personas; **auto-triggered by the decider**
  as of v2.1.4 (was defect D7, now closed). Catalog grown to **~143** with documented sources/licenses
  (`PERSONAS.md`). ✅
- **P2** Persona matching — word-overlap + name-weighted + synonym expansion (D8, v2.1.4). 🔌
- **P2** Empirical persona ratings — `lathe agent rate`: field-probe + independent judge scores a persona. 🔌
- **P2** Persona priority/mandatory config — user pins which experts are always/never consulted. 🔌
- **P2** **SDLC authoring** — `lathe sdlc "<goal>"` (v2.2.0): analyst authors UC→BR→FR→TS with stable IDs; the
  RTM gate refuses orphans/dangling refs; the `sdlc` workflow chains it into ack → STRICT build → trace →
  review. ⚙️ (RTM gate reproduced — orphans/dangling refs refused, refusal writes nothing)
- **P2** Select-K quality judge — collect K passing candidates, pick the cleanest. 🔌
- **P2** Grounding pre-step — cite real `file:symbol` before authoring a plan. 🧠

## Bucket E — Autonomy & orchestration
- **P1** Objective/goal loop — drive the harness toward an objective (budgets + Rule-of-Three). ✅
- **P1** Kanban board — durable sqlite task store (pending/in_progress/done/blocked/escalated). ✅
- **P1** Self-feed driver — one cheap cycle: objective → build → verify → ledger. ✅
- **P2** DAG / dispatcher / driver — dependency ordering + ready-task dispatch. 🔌
- **P2** Auto-decompose — split a big goal into a board of plan-tasks with deps. 🔌
- **P2** Dormancy — `wait`/`resume`/`waiting`: park a task on a signal, resume from durable state. ✅
- **P1** Rule-of-Three — a task failing 3× is escalated, not ground on. ✅
- **P2** Escalate-to-human — board `escalated` + ledger + ping. ✅

## Bucket F — Cleanliness & tree hygiene (so an AI never chases the wrong version)
- **P0** One canonical live implementation per capability — registry + `lathe whatis` (source of truth). ✅
- **P1** Stale/backup/dup gate — build FAILS if relics linger; tree stays pristine intrinsically. ✅
- **P1** Gated check-in — `lathe checkin` refuses to commit/push with relics, red gates, or behind upstream. 🔌
- **P2** `clean` — quarantine corrupt/relic files to `_archive/`. 🔌
- **P2** `dups` — AST structural-duplication detector (renamed-var safe). 🔌

## Bucket G — Token efficiency & context
- **P1** Repo-map — ctags code STRUCTURE (names/kinds/signatures) instead of full files → far fewer tokens. 🔌
- **P1** Skeleton-fill — model fills only a small `__FILL__` region of a scaffold → far fewer tokens. 🔌
- **P1** Skeleton-complete — no `__FILL__` → **0 model tokens**, gate deterministically. 🔌
- **P2** Doctrine preload (`CLAUDE.md`) — model knows the rules without re-deriving them each run. ✅

## Bucket H — Safety & security
- **P0** Plan validator — closed-rule (allowlist imports, no dunders, pure-literal exec fields) → a
  prompt-injected/malicious plan is refused before anything runs. ✅
- **P0** Sandbox isolation tiers — subprocess / docker / docker-ssh, fail-closed. ✅
- **P1** SSRF/exfil guard on the analyst URL (loopback/private only, DNS-rebind pinned). ✅
- **P1** Provenance markers — engine only overwrites files it generated (line-1 marker). ✅
- **P1** MCP input guards — `reject_flags` (fail-closed) + `is_within_root` (symlink-safe). ✅
- **P2** Secret redaction in logs; MODULE_NAME path-traversal guard. ✅
- **P2** `safe_write` (atomic + syntax gate + deny-list) — built, NOT yet wired into the loop. 🔌

## Bucket I — Distribution & integration (how you run it)
- **P0** Standalone CLI + `chat` REPL — its own shell. ✅
- **P0** MCP server — `build/verify/gate/review/do` as tools inside Claude Code / Cursor / Copilot. 🔌
- **P1** Pluggable analyst — Claude proxy ($0 sub) / any OpenAI-compatible / a human. ✅
- **P1** Pluggable implementer — Ollama / llama.cpp / vLLM / LM Studio / local / Claude. ✅
- **P1** Programmatic / embedded — import the engine; driven by any shell-running agent. ✅
- **P2** Claude skill 🔌 · plugin manifest 🔌 · PyPI packaging 🔌 · config file (env>config>default) ✅.

## Bucket J — Workflows (the harness runs in modes, not just "build")
- **P1** Named contract-driven workflows with fail-loud PASS/BLOCKED verdicts: `code-review`, `bug-fix`,
  `enhancement`, `doc-review`, `new-project`, **`sdlc`** (clarify → assume → ack → STRICT build → trace →
  review). bug-fix/enhancement/sdlc now carry an explicit **assumption-audit step**. ✅

## Bucket K — Observability & honesty
- **P1** Structured run logs — `runs/<id>.jsonl`, secrets redacted; a bug report is self-diagnosing. ✅
- **P1** Metrics surface — build success / cost split / churn from the ledger. ✅
- **P2** Run reports (`RUN_REPORT.md` + METRICS_JSON); honest benchmark; issue queue; `selftest`. ✅

---

## Cross-bucket P0 flagships (the story to lead with)
"Flagship" = most differentiating, **not** "autonomous" — status shown per item so this isn't misread as the
shipped-autonomous surface.
1. **Hard test gate** (C) — acceptance, not repair. ✅
2. **Content-hash pinning / byte-identical rebuilds** (B) — the feature no competitor ships. ✅
3. **Per-function spec+test granularity** (A) — why a cheap local model can be reliable. ✅
4. **The repair feedback loop, no escalation** (D) — the "agentic loop" that fixes the spec, not the model. ✅
5. **One canonical per capability + pristine tree** (F) — an AI never chases the wrong version. ✅
6. **Plan validator + nonce sandbox** (H) — the safety spine that makes running model output trustworthy. ✅
7. **Runs anywhere: standalone ✅ / inside your agent via MCP 🔌 / any model ✅** (I) — adoption path.
   (MCP is built + tested but not on the autonomous path yet — don't promise "run it in Claude Code today"
   as shipped-autonomous.)
8. **Methodology enforcement stack — 6 mechanisms shipped, seven gates** (C) — regression-proof #1 ·
   traceability #2 · mutation-score #3 · test-ack #4 (*partial oracle*) · test-kind #5 · gate-glue #6 ·
   assumption gate, composed by STRICT (v2.1.4→v2.6.1). ⚙️ The positioning centerpiece: *the SDLC process is
   enforced by the build, not left to discipline.* Scope guard: opt-in/STRICT-forced; comprehensiveness
   measured **per gated function, not whole-program**; #4 is a human re-read, not a second independent author;
   each gate is a tripwire, not a proof. See `METHODOLOGY_ENFORCEMENT_VALIDATION.md`.
9. **No silent guessing — the two front-ends** (D) — `lathe clarify` (interrogate the goal) + the adversarial
   `assumption-auditor` (audit the spec). ✅ as advisory front-ends (Step 0 of `sdlc`); enforcement is the
   ⚙️ assumption gate that refuses the build on an unconfirmed material assumption. The sharpest answer to
   "the AI just confidently does the wrong thing." Honest scope: surfaces/structures ambiguity, doesn't
   guarantee the human's answers are right.

## Infographic set — grounded in the prioritized buckets
A constructive, trustworthy, intuitive set. Each maps to buckets/flagships above; each states status honestly
(don't render a 🔌 capability as if it ships autonomously). Existing four in `docs/infographics/` cover the
first tier; proposed additions cover the under-sold P0/P1 strengths surfaced this round.

**Have (keep):**
1. `01_build_loop` — how it works (A+C+B+D). ✅
2. `02_division_of_labor` — analyst vs implementer, model-agnostic (D+I). ✅
3. `03_strengths` — 5 strengths (C·B·A·I·H sampler). ✅
4. `04_determinism` — pin+reuse = same code (B). ✅

**Propose (fills the gaps, in priority order):**
5. **"One harness, many jobs"** (J + E) — the workflow modes (build · review · bug-fix · enhance ·
   doc-review · new-project), each contract-driven with a fail-loud verdict. *Answers "it's not just codegen."*
6. **"The loop that learns"** (D) — implementation harness ↔ thinking harness: gate fails → banked failure →
   analyst sharpens the SPEC → regenerate; no escalation. *The "agentic loop" story, done honestly.*
7. **"A tree an AI can't get lost in"** (F) — one canonical per capability, pristine gates, gated check-in.
   *The relic/duplicate-confusion problem, structurally solved.*
8. **"Cheap context: read the map, not the files"** (G) — repo-map + skeleton-fill/complete → fewer tokens.
   *The token-efficiency lever.* (Mark 🔌.)
9. **"Three ways to run it"** (I) — standalone shell ✅ · inside your agent via MCP 🔌 · embedded ✅;
   pluggable analyst + implementer. *The adoption path — with honest status badges.*
10. **"The safety spine"** (H) — plan validator (data-only) + nonce sandbox (unforgeable verdict) + isolation
    tiers. *Why running model-written code here is trustworthy.*

Design rules for the set (carried from the review's trust standard): every graphic shows real status
(✅/🔌/⚙️), never implies a 🔌 capability is shipped-autonomous or a ⚙️ opt-in gate is on by default; the
"cheap local model" economics are framed as the default + an invitation to test (not a proven result — see
`LATHE_REVIEW_V2.md` §4/§14). The v2.1.3-era omissions have since landed (decider auto-fetch / §15 D7 fixed
in v2.1.4) and the methodology-enforcement gates (#1/#2/#3) are now real — a graphic on them must carry the
⚙️ *opt-in / STRICT-forced* scope and the *per-gated-function, not whole-program* comprehensiveness caveat
(see `METHODOLOGY_ENFORCEMENT_VALIDATION.md`).

## Question for the harness reviewer
Is this inventory COMPLETE (any shipped capability missing?) and are the buckets + P0/P1/P2 priorities
accurate to what the code actually implements (any capability mis-prioritized, or any 🔌/🧠 mislabeled as ✅)?
