Grounding confirmed. Here is the adversarial critique and hardened spec.

---

# `lathe verify` — Adversarial Hardening Spec (implementer-facing)

Grounded in `engine_v2.py` (the real engine; `ENGINE` at `lathe.py:59`), `cmd_verify` (`lathe.py:381`), `REPRODUCIBILITY.md`, `docs/OPERATING_CONTRACT_DESIGN.md` item 8. The proposal is directionally right but **structurally trusts an engine that was never built to be a witness**. Every hole below is a place the run can PASS or emit an attestation *without doing the work*.

## Part A — Holes (skip / produce-nothing / vacuous-pass), each with its deterministic closer

**H1 — Engine exits 0 even when the rebuild fails; verify inherits a false PASS.**
`engine_v2.py` only `sys.exit`s nonzero on *refusals* (STRICT/assumption/path gates, lines 105/172/221/462/890). A normal build where a function fails to generate prints `NEEDS SPEC REFINEMENT` and **exits 0** (tail at 1121–1197 has no failure exit). Today `cmd_verify` does `rc=_run(...)` and returns it — so verify already passes vacuously on an incomplete rebuild. Any design that reads engine's exit code inherits this.
- **Closer:** Verify must NOT trust exit code. It ingests the machine-readable metrics block (`===METRICS_JSON_BEGIN===`/`END`, line 1180) and asserts `build_ok==true AND functions_passed==functions_total AND functions_total>0`. Missing/malformed metrics block ⇒ hard REFUSE (H6).

**H2 — Engine always mutates the *real* OUT_DIR; "read-only / isolated scratch" is not achievable by calling `engine_v2 <plan>`.**
OUT_DIR is derived from the plan's `OUT_DIR` attr via `resolve_out_dir` (`_pre_out`, line 469). The engine writes `.pins.json` (atomic replace, 927–928), `MODULE_NAME.py`, `RUN_REPORT.md`, `runs/<run_id>.jsonl`, and appends `metrics/runs.jsonl` (1190–1194) — the last two are **independent of OUT_DIR**. So rebuild#1 pollutes the real pins, and "side effects: none" is false.
- **Closer:** Verify constructs an isolated scratch tree per rebuild: copy the plan, copy `.pins.json` into a scratch OUT_DIR, and run engine with (new, required) env overrides `LATHE_OUT_DIR_OVERRIDE`, `LATHE_METRICS_PATH=<scratch>/m.jsonl`, `LATHE_RUNS_DIR=<scratch>/runs`. Deterministic post-check: assert `sha256(real .pins.json)` and `mtime` are **unchanged** before vs after each rebuild (snapshot in P0, re-assert in P4). If changed ⇒ REFUSE. Engine needs an OUT_DIR override env (does not exist today).

**H3 — "0 model calls" is measured, not forbidden; a pin miss silently *generates* into scratch pins.**
There is no null transport. `call_model`→`_call_model_impl` hits urllib (283/296/306). On a pin miss the engine *generates* and pins. The proposal's null transport must live **inside the engine**, not in the verify wrapper — a wrapper cannot prevent the HTTP call that already happened.
- **Closer:** Add `LATHE_OFFLINE=1` to the engine: `call_model` raises a typed `OfflineViolation` and the engine `sys.exit`s nonzero printing a machine line `PIN_MISS <function_name>`. Verify sets `LATHE_OFFLINE=1` for all rebuilds. G2 then asserts `tok_total==0 AND claude_calls==0` from metrics **and** that no `PIN_MISS` line was emitted.

**H4 — G2 (tokens==0) is independent of G1 (zero-miss); tokens can be 0 on a *failed* run.**
With the offline guard, a miss aborts *before* any HTTP call, so `tok_total` stays 0 even though the run didn't reproduce. Reading only `tok==0` would PASS a run that actually missed.
- **Closer:** G1 is asserted from `per_function[*].src == "pinned"` for **every** function (metrics carries `per_function` with `src`, line 1176), not from token count. G1 and G2 are separate gates; both required. A `PIN_MISS` line forces G1 FAIL by name.

**H5 — G3 byte-identical can match a STALE module the engine never rewrote.**
The module is only written when `module_ok` (1130). On any function fail the old `MODULE_NAME.py` on disk is untouched — comparing "produced module" to reference could compare *the same stale file to itself*. In scratch this manifests as: if engine doesn't write, the scratch module is absent or stale.
- **Closer:** G3 requires (a) `module_ok==true` in metrics, (b) the scratch module file exists and was written *this run* (mtime within run window / file created in the empty scratch dir), (c) `sha256(scratch#1)==sha256(reference)==sha256(scratch#2)`. Absent scratch module ⇒ FAIL, not skip.

**H6 — Metrics ingestion is stdout scraping; malformed/missing ⇒ silent falsy defaults ⇒ vacuous pass.**
If verify greps the METRICS markers and a run dies mid-way (H1 refusals `sys.exit` before line 1180), the block is absent; a naive parse yields `{}`, and downstream `.get("failed",0)`-style reads look green.
- **Closer:** Parsing is fail-closed: exactly one well-formed JSON object between the markers, required keys present (`build_ok, functions_total, functions_passed, per_function, tok_total, claude_calls`), else REFUSE with `reason="metrics_unparseable"`. Never default a missing key to a passing value.

**H7 — Empty / zero-function plan attests reproduction of nothing.**
`all_ok=True when not FUNCTIONS`; module may be HEADER+GLUE only. G1 (no functions to miss), G3 (trivially stable), G4 (nothing to revalidate) all pass vacuously ⇒ `reproduced:true` for a plan that pins nothing.
- **Closer:** P0 REFUSE-guard: `functions_total>0 AND pins_entry_count>0 AND at_least_one_pin_maps_to_a_plan_function`. Nothing to attest ⇒ verdict `REFUSE` (reason `empty_subject`), never PASS.

**H8 — Dirty-tree fallback to "double-rebuild-only" is itself vacuous and must not yield an attestation.**
Two offline rebuilds from the *same* pins in the same process read the same pin blobs and concatenate them the same way — they are byte-identical almost by construction. That proves *assembly stability*, not *reproduction of the committed artifact*. The proposal flags drift but still allows `verdict: PASS` and emits the attestation.
- **Closer:** When the reference is unavailable/dirty/hand-edited, verify still runs both rebuilds but **withholds the attestation**: `attestation: null`, `verdict: PASS_DEGRADED` (a distinct verdict a release gate must not accept as proof-of-determinism), `drift[]` records the reason. Only a *committed, clean, provenance-marked* reference module yields `reproduced:true`.

**H9 — G4 pin re-validation is vacuous for pins whose tests list is empty.**
Engine `validate()` loops over `tests`; an empty list returns green trivially (same pattern as `engine.py:82`). "Every pinned impl still passes its tests" is satisfied by pins that assert nothing.
- **Closer:** G4 counts *assertions actually executed*: require `revalidated_with_tests == functions_total` where each counts only if `len(tests)>=1` and all ran. Any pinned function with zero tests ⇒ G4 FAIL (reason `untested_pin:<name>`), reported by name. Emit `pins_without_tests[]`.

**H10 — G5 closed-pin-graph is *always* green in verify because nothing is "fresh."**
Engine's transitive invalidation (`_pin_stale_by_deps`, `_fresh_fn_names`, lines 515–528) only fires for functions *regenerated this run*. In an offline zero-gen rebuild there are no dirty seeds, so the closure check finds nothing and G5 passes **without inspecting the committed pins at all** — the exact "placeholder that passes without doing the work."
- **Closer:** G5 in verify must run a **from-scratch static closure** over the committed pins (not the incremental build-time check): for each pinned function, extract its referenced dependency names from the pinned source, resolve each to a pin, and confirm the depended-on pin's *current* code equals the code this pin was validated against. Any dangling/mismatched edge ⇒ G5 FAIL with the offending edge. `tools/pin_deps.py` (line 522) supplies dep extraction; the closure walk is new deterministic code.

**H11 — Adversarial pin-eviction probe passes vacuously (wrong pin, or wrong abort cause).**
"Evict one pin, confirm a MISS" is under-specified: evicting a pin not referenced by the plan ⇒ no miss ⇒ probe wrongly concludes "pins not load-bearing" or is skipped; and `OfflineViolation` from *any* cause (plan load error, etc.) would be counted as "miss detected."
- **Closer:** Probe is **differential and named**: (1) run baseline offline rebuild, assert 0 misses; (2) pick a pin key `k*` that provably maps to a plan function `f*`; evict only `k*` from a scratch copy; rerun; assert the engine emits exactly `PIN_MISS f*` (that specific name) and nonzero exit. Both arms required: `baseline_miss_free==true AND eviction_miss_is[f*]==true`. Otherwise probe FAIL.

**H12 — Source-shuffle-stable probe as written is incoherent (module assembly IS order-dependent).**
Engine assembles `HEADER + [solved in plan.FUNCTIONS order] + GLUE` (line 123 in engine.py; same in v2). Shuffling `FUNCTIONS` order **changes the bytes** — so `source_shuffle_stable:true` is either always-false for a correct engine or the stub tests nothing. The real invariant is that pin *resolution* (the key = `sha256(name+prompt+tests+model)`) is position-independent, while emitted order deterministically follows the declared order.
- **Closer:** Reframe the probe to the true invariant: shuffle plan `FUNCTIONS`, rebuild, and assert (a) the **set of pin hits is identical** (every function still `src=="pinned"`, no new miss) — proves lookup is order-independent; and (b) re-sorting the emitted function blocks back to declared order reproduces the reference bytes — proves emission order is a pure function of declared order, not hash-map iteration. Report `pin_lookup_order_independent` and `emission_order_deterministic` separately.

**H13 — Cross-run tamper on `.pins.json` is undetectable; byte-identity proves internal consistency, not authenticity.**
Verify reads *whatever pins are present*. A maliciously rewritten `.pins.json` plus a co-generated module will rebuild byte-identically and PASS. Recording `pins_sha256` proves what verify saw, not that it is the original. This is the deepest hole: the security/supply-chain lens (max) has nothing to compare against.
- **Closer:** Verify anchors to a **prior committed truth**: compare `pins_sha256` against (in priority) the `pins_sha256` recorded in the last green *build* manifest under `docs/ce/`, else a committed `.pins.lock`, else the git-blob hash of `.pins.json` at HEAD. Mismatch ⇒ G-tamper FAIL (reason `pins_drift_since_build`), attestation withheld. If no anchor exists, `tamper_check: "unanchored"` and attestation is downgraded to `PASS_DEGRADED` (H8) — reproduction from unauthenticated pins is not proof-of-determinism.

**H14 — The attestation is a forgeable plain JSON blob.**
Downstream `checkin`/release consumes `{reproduced:true,…}`. Nothing binds it to the run that produced it.
- **Closer:** Attestation carries a self-hash: `attestation_sha256 = sha256(canonical_json(attestation_without_this_field))`, and the manifest carries `manifest_sha256` over its own canonicalized content. The release gate recomputes both. Not cryptographic signing, but it makes casual edits detectable and gives the downstream gate a fixed thing to pin.

**H15 — Manifest can be skipped when the engine (or verify's own P3) hard-exits.**
Engine `sys.exit`s on refusals (H1 list); verify's scratch-copy step can raise (disk full). If the manifest write is inside the happy path, a crash produces **no record** — violating "always emitted."
- **Closer:** The dispatcher wraps P1–P4 in `try/…/finally`; the `finally` **always** writes `docs/ce/<run_id>.manifest.json` with a valid `verdict` (`PASS`/`PASS_DEGRADED`/`REFUSE`) and, on exception, `reason` + traceback digest. A separate deterministic **manifest-schema gate** validates the emitted JSON against the required-fields schema *before* the process is allowed to exit 0; a manifest missing any required key is itself a REFUSE.

**H16 — `casual` thinking level is a vacuous-attestation generator.**
Proposed casual = rebuild#1 vs reference only, assumption defaulted silently, pin-revalidation skipped. Pin re-validation is free (0 tokens) and is the *one* thing that catches env drift the pins can't. Skipping it while still emitting `reproduced:true` ships an attestation with near-zero scrutiny.
- **Closer:** Floor the levels: **every** level runs pin re-validation (G4) and G1/G2/G3 — these are cheap and load-bearing. The dial buys *lenses and probes*, never removes a gate. The **attestation itself requires ≥ medium**: at `casual`, always emit the manifest but `attestation: null` (verdict may still be PASS for a human, but no machine proof-of-determinism is minted).

---

## Part B — Hardened workflow (typed steps + guards)

**P0 · Intake — AUTO (non-bypassable).** Assign `run_id`; resolve+validate plan (`_resolve_plan`/`_validate_plan_file`); resolve real OUT_DIR/`.pins.json`; **snapshot** `sha256(.pins.json)` + its mtime, `sha256(reference module)`, `git_rev`, `tree_dirty`, env fingerprint. **Guards (REFUSE on fail):** H7 subject-non-empty (`functions_total>0 ∧ pins_entry_count>0 ∧ ≥1 pin maps to a plan function`); engine supports `LATHE_OFFLINE` + `LATHE_OUT_DIR_OVERRIDE` (capability probe — if absent, REFUSE, don't silently degrade to online). Engage offline guard for the whole process.

**P1 · Front-end — YOU(gated)/AUTO.** `clarify` SKIPPED (read-only, recorded as such). Exactly one audited assumption — the byte-identical reference — resolved fail-closed by `assumption-auditor`: clean committed provenance-marked module ⇒ reference; else fallback + **attestation-withheld flag** (H8). Record env baseline. No `.decisions.md` write.

**P2 · Selection — AUTO + data.** Minimum lens set, each with a one-clause why: `reliability` (always, determinism/drift), `data-integrity` (high+, pin/module authenticity + H10 closure), `devops-cloud` (high+, env-fingerprint caveat), `security`/supply-chain (max, H13 tamper anchor). Lenses parameterize gates; they do not gate themselves.

**P3 · Work — AUTO.** (1) Snapshot (from P0). (2) **Rebuild#1** in isolated scratch, `LATHE_OFFLINE=1`, capturing metrics JSON (fail-closed parse, H6). (3) **Rebuild#2** in a *second* scratch. (4) **Pin re-validation** counting executed assertions (H9). (5) Post-assert real `.pins.json` sha+mtime unchanged (H2). Levels ≥high add the differential eviction probe (H11) and shuffle probe (H12); max adds the H13 tamper-anchor comparison and full closure dump.

**P4 · Adversarial gate — GATE (all pass or REFUSE):**
- **G1 zero-miss** — every `per_function.src=="pinned"`; any `PIN_MISS` ⇒ FAIL by name (H4).
- **G2 zero-calls** — `tok_total==0 ∧ claude_calls==0 ∧ no PIN_MISS` (H3).
- **G3 byte-identical** — `module_ok ∧ scratch module freshly written ∧ sha(#1)==sha(ref)==sha(#2)` (H5).
- **G4 pin-revalidation** — `revalidated_with_tests==functions_total`, no untested pins (H9).
- **G5 closed-pin-graph** — from-scratch static closure over committed pins, no dangling/mismatched edge (H10).
- **G6 no-real-mutation** — real OUT_DIR pins sha+mtime unchanged (H2).
- **G7 tamper-anchor** — `pins_sha256` matches prior build-manifest/lock/HEAD blob, or `unanchored`⇒degrade (H13).
- **G-probe** (≥high) — differential eviction names `f*` (H11); shuffle proves lookup-order-independence + emission determinism (H12).

**P5 · Manifest — AUTO in `finally`, never optional (H15).** Emit `docs/ce/<run_id>.manifest.json` + render on PASS/PASS_DEGRADED/REFUSE. A **manifest-schema gate** validates required keys before exit; missing keys ⇒ REFUSE. On PASS (≥medium, clean reference, anchored pins) additionally embed the self-hashed attestation (H14).

---

## Part C — Hardened manifest (exact fields; deltas from the proposal called out)

```json
{
  "run_id": "verify-2026-07-04T...-<shorthash>",
  "manifest_sha256": "<sha256 of this object minus this field>",   // H14
  "invocation": "verify",
  "plan": "examples/hello.py",
  "goal": "attest byte-identical reproduction from committed pins at zero model calls",
  "thinking_level": "medium",
  "engine_capabilities": {"offline_guard": true, "out_dir_override": true},  // H0/H3 probe; false => REFUSE
  "front_end": {
    "clarify": "skipped (read-only)",
    "assumptions": [{"item":"byte-identical reference","resolution":"git HEAD committed module",
                     "fallback_taken": false, "materiality":"high","auditor":"assumption-auditor"}],
    "environment_baseline": {"python":"3.10.14","platform":"linux-x86_64","key_libs":{"...":"..."}}
  },
  "selection": {"lenses":[{"lens":"reliability","why":"..."},{"lens":"data-integrity","why":"..."}]},
  "subject_guard": {"functions_total": 7, "pins_entry_count": 7, "pins_mapping_plan_fns": 7, "nonempty": true}, // H7
  "inputs": {
    "pins_sha256":"...","pins_entry_count":7,"reference_module_sha256":"...",
    "reference_available": true, "reference_provenance_marked": true,   // H8
    "git_rev":"07bbd6a","tree_dirty":false,
    "real_outdir_pins_sha_before":"...","real_outdir_pins_mtime_before": 0  // H2/G6 anchor
  },
  "contributors": [
    {"step":"rebuild#1","type":"auto","scratch_dir":"...",
     "found":{"module_sha256":"...","module_written_this_run": true,"module_ok": true,
              "model_calls":0,"tok_total":0,"claude_calls":0,"pin_miss":[],
              "per_function":[{"name":"add","src":"pinned","module_bytes_sha":"..."}]}},
    {"step":"rebuild#2","type":"auto","found":{"module_sha256":"...","module_written_this_run": true}},
    {"step":"pin_revalidation","type":"auto",
     "found":{"revalidated":7,"revalidated_with_tests":7,"failed":0,"pins_without_tests":[]}}, // H9
    {"step":"static_pin_closure","type":"gate",
     "found":{"edges_checked":9,"dangling":[],"mismatched":[]}},   // H10
    {"step":"adversarial_probe","type":"gate",
     "found":{"baseline_miss_free": true,"evicted_key_for":"add","eviction_miss_is":"add", // H11
              "pin_lookup_order_independent": true,"emission_order_deterministic": true}}  // H12
  ],
  "gate_verdicts": {
    "G1_zero_miss":{"pass":true,"misses":[]},
    "G2_zero_calls":{"pass":true,"tok_total":0,"claude_calls":0,"pin_miss":[]},
    "G3_byte_identical":{"pass":true,"ref_sha":"...","rebuild1_sha":"...","rebuild2_sha":"...","module_ok":true},
    "G4_pin_revalidation":{"pass":true,"revalidated_with_tests":7,"untested_pins":[]},
    "G5_closed_pin_graph":{"pass":true,"dangling":[],"mismatched":[]},
    "G6_no_real_mutation":{"pass":true,"pins_sha_unchanged":true,"pins_mtime_unchanged":true},   // H2
    "G7_tamper_anchor":{"pass":true,"anchor":"build_manifest","expected_pins_sha256":"...","actual":"...","status":"matched"} // H13
  },
  "drift": [],
  "models": {"generation":"none (offline guard)","analyst":"none"},
  "cost": {"tokens_prompt":0,"tokens_completion":0,"usd":0.0},
  "timing": {"total_ms":1840,"rebuild1_ms":610,"rebuild2_ms":590,"revalidation_ms":520},
  "verdict": "PASS",   // PASS | PASS_DEGRADED | REFUSE   (H8/H15)
  "refuse_reason": null, // set on REFUSE: empty_subject|metrics_unparseable|engine_incapable|pin_miss|byte_mismatch|untested_pin|graph_open|real_mutation|pins_drift_since_build|manifest_schema
  "attestation": {       // null at casual, on any degrade/refuse, dirty reference, or unanchored pins (H8/H13/H16)
    "reproduced": true, "plan":"examples/hello.py","pins_sha256":"...","module_sha256":"...",
    "env_fingerprint":"py3.10.14/linux-x86_64","run_id":"verify-...",
    "attestation_sha256":"<self-hash>"   // H14
  }
}
```

**Verdict logic (deterministic):** `REFUSE` if any P0 guard or any G1–G7 fails, or manifest-schema gate fails. `PASS_DEGRADED` if all gates pass but reference is dirty/unanchored/`casual` (attestation withheld). `PASS` only if all gates pass, reference clean+anchored, level ≥ medium — the only path that mints `reproduced:true`.

---

## Part D — Engine changes this spec requires (do not skip; the wrapper cannot fake them)

1. `LATHE_OFFLINE=1`: `call_model` raises `OfflineViolation`; engine prints `PIN_MISS <name>` and exits nonzero. (Closes H3/H4/H11 — without it, a miss silently generates into scratch pins.)
2. `LATHE_OUT_DIR_OVERRIDE` (+ `LATHE_METRICS_PATH`, `LATHE_RUNS_DIR` already exist as env). Lets verify redirect *all* writes to scratch. (Closes H2/G6.)
3. Metrics block already exists (`===METRICS_JSON_BEGIN===`, line 1180) and already carries `per_function[].src`, `tok_total`, `claude_calls`, `build_ok`, `module_ok` — verify must consume it fail-closed rather than scrape human text.

The single sentence that captures the whole hardening: **verify must treat the engine, the pins, and its own happy path as adversaries** — assert reproduction from the metrics contract (not exit code), forbid generation in the engine (not measure it after), anchor pins to a prior committed truth (not just hash what's present), run G5 as a from-scratch closure (not the build-time incremental no-op), and mint the attestation only on the clean/anchored/≥medium path while always emitting a manifest in `finally`.