# Operating Contract — Implementation Spec (for the maintainer/implementer)

> **✅ STATUS — IMPLEMENTED & VERIFIED (v2.10.0–v2.13.1).** Phase 0 (per-invocation manifest, v2.10.0),
> Phase 1 (enforcement spine, v2.11.0), Phase 2a (19 workflows + promotion + U2 STRICT clamp, v2.12.0),
> the 2a follow-up (manifest names its resolved workflow, v2.13.1), and #11 (adversarial-synth gate, v2.13.0)
> all shipped and were independently re-probed (guard-forge defeated, manifest un-skippable, `spine_gate` /
> `manifest_contract_gate` 5/5). The persona `selection` backing (#9) merged via PR #13 (UCB1 reachability
> verified 143/143, feature-flagged `LATHE_PERSONA_UCB`). This doc is retained as the build record; it reads
> in the future tense but describes shipped, verified behavior.

*The build spec for the enforced, uniform, recorded operating contract. Design source: a 40-agent harness
brainstorm (manifest schema + enforcement spine designed from the real code; all 19 invocation workflows
adversarially hardened). Grounded designs live beside this file — read them; this is the sequencing,
the standing requirements, and the acceptance bar.*

## Prime directive (owner-set priority)

1. **Report generation is Phase 0 — build it FIRST.** The per-invocation manifest is the *evaluation
   instrument*; until it exists, nothing else can be judged holistically. Everything else waits on it.
2. **Build through the harness.** Every harness-buildable module (pure decision/logic) goes spec+tests →
   regenerate under the gates — never hand-patched. Only genuine trunk (`lathe.py` dispatch, `engine_v2.py`
   core, qa infra) is hand-edited, and each hand-edit must be **called out explicitly** in the commit.
3. **Emit the reports.** Every phase's work must produce the manifest/report described here — those manifests
   are the artifacts the reviewer evaluates. A feature is not "done" until its invocation emits a complete,
   schema-valid manifest.

## Phase 0 — The manifest / report generator  ▸ `MANIFEST_DESIGN.md`

Build the deterministic report first. From the design (grounded to real lines):

- **New pinned tool** `tools/manifest.py` — `begin / append_contributor / record_gate / set_selection /
  set_outcome / finalize`. Pure assembly + atomic write + self-hash. No model calls.
- **Schema** `schema_version 1.0.0` → `docs/ce/<run_id>.manifest.json` + a deterministic `.md` render.
  Every field present on every emission (nulls, not omissions). Captures: invocation/argv, intake+thinking,
  front-end Q&A + assumptions, selection **with a `why` per pick**, `contributors[]` with **verbatim**
  findings + per-role tokens/cost/timing, gate verdicts with evidence, models + `usage` (tokens **and** USD,
  split by role), timing by phase, outcome, and an `integrity` self-hash.
- **Close the analyst-token gap (the three real layers):** L1 `claude_proxy.py:189` hardcodes `usage:0` →
  emit real CLI usage; L2 `engine_v2.py:287` (claude branch) never reads `usage` → read + attribute by role;
  L3 flat `tok` → per-role buckets + a versioned `tools/pricebook.py` for USD + a `completeness` invariant
  that makes any un-attributed call **visible and test-failing**. Kill the literal `"NOT INSTRUMENTED"`
  string (`engine_v2.py:1145`).
- **Acceptance (T1–T8 in the design):** T1 emission universal across all ~35 entry points; **T2 un-skippable
  under return/raise/SystemExit/SIGINT** (the `finally`-emit); T3 schema completeness; **T4 analyst tokens
  instrumented + never regress**; T5 cost present + role-split; **T6 bare command routes through contract**;
  T7 findings byte-verbatim; T8 determinism/self-hash. T2/T4/T6 are load-bearing.

## Phase 1 — The enforcement spine  ▸ `ENFORCEMENT_SPINE_DESIGN.md`

Make the contract non-bypassable, reusing the single chokepoint `main(argv)` (`lathe.py:1687`).

- Split `main` → public `run_spine` + private `_dispatch`; a **re-entrancy guard** (`_LATHE_SPINE_RUN`,
  FORCE-cleared at process entry like the existing `:1688` pattern) so bare commands run *through* their
  contract and inner workflow steps re-enter raw. New pinned `tools/spine.py`.
- **Six phases in code around the data:** intake → front-end → selection → work → adversarial gate →
  `finally: emit()`. A workflow (data) can define bad steps but **cannot delete a phase**.
- `CONTRACT_FOR` (command→contract) + a **thinking-depth table** (`casual/medium/high` → tries / select-N /
  assumption-policy / adversarial), stamped via the existing `setdefault` precedence (operator env wins).
- **Stress test** `tools/test_spine_enforced.py` (+ a grep-gate in `qa/run_gates.py`): coverage of every
  entry point, exactly-one-manifest, the **guard-forge attack**, the **skill-subprocess attack**, order/halt,
  manifest-on-crash, single-raw-path invariant. No invocation may run around its contract.

## Phase 2 — The 19 invocation workflows  ▸ `workflows/<id>.md`

Each invocation has an adversarially-hardened spec: every place a step could be skipped, produce nothing, or
pass vacuously, with the **deterministic guard** (code, not skill judgment) that closes it. Extend
`workflows.py` from 6 to all 19 and wire them under the spine. Notable real holes the hardening already
found (fix as part of this):

- `run_gates.py` **silently `continue`s past a missing gate file** and still prints "regression clean" → a
  vacuous green. (`code-review`, `gate-quality`)
- The review path **never writes `ratings.json`** and there is **no `usage.jsonl`** → "graded personas" is
  today vacuously match-only. (`code-review`, `select-grade-experts`) — couples to issue #9.
- `hreview.py` emits **unparseable free text**, truncated `[-4000:]` → downstream "for each finding" has no
  list. (`code-review`, `doc-review`)

The 19: build-from-goal, build-from-plan, autonomous, enhancement, bug-fix, code-review, doc-review,
verify-reproduce, gate-quality, clarify-goal, sdlc-requirements, assumption-audit, trace-inspect,
select-grade-experts, onboard-project, ship-release, maintain-tree, serve-api, report-triage.

## Coupled issues

- **#9 (persona redesign)** — the usage ledger + grade-weighted selection + explore/exploit are the backing
  for the `selection` block of the manifest; land them together.
- **#11 (adversarial test synthesis)** — becomes the Phase-4 `adversarial-synth` gate every write-invocation
  inherits.

## How the reviewer evaluates (the loop)

As each phase lands, the reviewer will **stress-test the emitted manifests** with executable probes (same
method used on the gates): drive real invocations, assert the manifest is complete, verbatim, cost-attributed,
and un-skippable (T2/T4/T6 and the spine attacks). "Done" = the manifest proves it, not a claim.

## Provenance

Designed via a harness multi-agent brainstorm (40 agents, 0 errors): two foundation cells (manifest, spine)
+ design→adversarial-harden per invocation. Every design is grounded to real file:line anchors; verify before
implementing — the reviewer will.
