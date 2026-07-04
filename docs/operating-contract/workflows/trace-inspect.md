I have deep grounding in the real code. Here is the adversarial critique and hardened spec.

---

# `trace-inspect` — Adversarial Teardown + Hardened Spec

Grounded in the actual code: `lathe.py` `cmd_trace` (1560), `cmd_metrics` (472), `cmd_status` (335), `cmd_whatis` (678), `main` dispatch (1694); `trace_logic.trace_rows` (45), `metrics_summary` (4), `registry.load/whatis/audit`. Verified facts that drive the attack surface: **`docs/ce/` is currently empty/absent** (0 files); `metrics_summary` **swallows malformed JSONL** (`cmd_metrics` line 485 `pass`); `trace_rows` is wrapped in **blanket `except: continue`** at every level; `cmd_trace` reads pins with `except: pins={}`; `registry.load` returns a `{"__error__":…}` sentinel that `cmd_whatis` **silently filters out**; `_probe` returns `"up (503)"` for a loading model; every handler `return`s from many points with no record.

---

## PART A — the one structural hole that voids the whole guarantee

**H0 — Emission is appendable, therefore skippable.** The design says "Manifest — AUTO, never optional" as *step 5*. But every existing handler returns early from 5–8 points (`cmd_trace`: `return 2` at 1567/1570, `return 1` at 1576, `return 0` at 1581, `return 0/1` at 1611; `cmd_metrics`: `return 0` at 477/495/501). If the manifest write is code at the *end of the handler*, **every early return bypasses it** — including the refusal path the design specifically promises records a record. "Always emitted" is a lie unless emission is not in the handler at all.

**Close it (non-negotiable, this is the spine):** emission is owned by a dispatcher wrapper, not the handler.

```
def run_contract(subcmd, argv, parent_ctx=None):
    m = Manifest.open(subcmd, argv, parent_ctx)      # run_id minted, ts_started, file path reserved
    try:
        m.result = HANDLERS[subcmd](argv, m)         # handler MUTATES m as it goes; returns verdict
    except Refuse as r:      m.refuse(r)
    except Exception as e:   m.error(e)              # crash -> ERROR manifest, still emitted
    finally:
        m.finalize_and_emit()                        # <-- the ONLY exit. atomic write, verified, or process aborts loud
    sys.exit(m.exit_code())
```

The handler no longer calls `print(); return N`. It writes into `m` and raises `Refuse`/returns a verdict. There is **no code path from dispatch to process-exit that does not pass through `finally: m.finalize_and_emit()`**. `main()`'s `table[cmd](rest)` (1705) is replaced by `run_contract(cmd, rest)`. Internal cross-calls (`cmd_checkin`→`cmd_gate` at 1626, `cmd_selftest`→`cmd_gate`, `cmd_chat`'s inline `status`) must call `run_contract(..., parent_ctx=m)` — a lint check (grep gate) that **no `cmd_*` is invoked except through `run_contract`** is itself a standing GATE, else the "route THROUGH the contract" invariant rots.

---

## PART B — enumerated holes (skip / produce-nothing / incomplete / vacuous)

Each: the attack, then the deterministic check that closes it.

### Manifest emission integrity

**H1 — Write target doesn't exist → produce nothing.** `docs/ce/` is empty/absent now. First real run: `open(path,"w")` raises, manifest lost.
→ **Check:** `finalize_and_emit` does `os.makedirs(CE_DIR, exist_ok=True)` then **atomic write**: `tmp = path+".tmp"; write; os.replace(tmp, path)`. Then **read-back-verify**: `json.load(open(path))` must round-trip and equal the in-memory dict's canonical form. On any failure, write to a fallback `CE_DIR/_emit_failures/<run_id>.json` and if *that* fails, emit the full JSON to stderr with a `LATHE_MANIFEST_EMIT_FAILED` banner and exit 3. Producing nothing is not a reachable state.

**H2 — Incomplete manifest passes as complete.** A code path forgets `ts_ended`/`gate`/`verdict`; a half-populated dict is written and looks authoritative.
→ **Check:** a static **required-fields schema** (`REQUIRED = {run_id, subcommand, argv, ts_started, ts_ended, intake, front_end, selection, sources, work, gate, verdict, render_sha256, manifest_path, cost}`). `finalize` validates presence+type before write. A missing field does **not** silently write and does **not** silently drop the record — it writes the manifest with `verdict:"ERROR"`, `schema_incomplete:[field,…]`, exit 3. Emission is never skipped; *completeness of emission is itself gated*.

**H3 — run_id collision → silent clobber.** `run_id = ts+sha8(argv)`: two `lathe status` calls in the same second have identical argv+ts → second `os.replace` overwrites the first. Records vanish.
→ **Check:** `run_id = <ts>Z-<sha8(argv)>-<pid>-<4hex nonce>`. `finalize` asserts the target path does **not** already exist (`O_CREAT|O_EXCL`); on collision, bump nonce and retry. No manifest overwrites another.

**H4 — Child path produces zero standalone record.** The design says a child invocation appends a `provenance` sub-record to the parent "instead of a new file." If the parent manifest isn't written yet, is being written concurrently, or `parent_run_id` env is stale/missing, the child writes nothing believing the parent will carry it — an orphaned inspection with no durable trace.
→ **Check:** **A child ALWAYS writes its own `docs/ce/<run_id>.manifest.json`** with `run_context: "child_of:<parent_run_id>"`. The parent linkage is a *cross-reference* (`children:[run_id,…]` appended to the parent, best-effort), never a *substitute*. "Append to parent instead of own file" is removed from the design. Durable record ⇔ own file, unconditionally.

**H5 — high-lens model call on the critical path.** `status`'s whole reason to exist is that endpoints may be down — including the analyst endpoint the `high` lens calls. If the model call throws/times out and emission is downstream of it, no manifest.
→ **Check:** the lens call is wrapped, time-boxed, and **strictly after** the deterministic gate has already set `verdict`. Failure appends `caveats:["lens_unavailable: <reason>"]` and `models_error`; it can never change a deterministic verdict nor block emission. Manifest is emittable with `model_calls:0` on every path.

### Faithfulness gate — vacuous-pass vectors

**H6 — Faithfulness re-runs the same function it's auditing (tautology).** The design's "recompute aggregates from raw rows, assert they reconcile with the summary" is vacuous if the recompute calls `metrics_summary` again — same code, same bug, guaranteed PASS. `metrics_summary` sums `functions_passed`; "assert Σrow.functions_passed == summary.functions_passed" against the same sum is `x==x`.
→ **Check:** the faithfulness checker is an **independent re-implementation** with a **declared formula table** (the aggregate is the spec, not the code):

```
FORMULAS = {
  "build_success_rate": ("builds_ok / runs", denom="runs"),
  "first_pass_rate":    ("first_pass / functions_total", denom="functions_total"),
  "avg_tries":          ("Σrow.avg_tries / runs", denom="runs"),
  "functions_passed":   ("Σrow.functions_passed"),
  ...
}
```

The gate recomputes each via the formula string's independent evaluator over the raw parsed rows and asserts equality to the *rendered* value **at the rendered precision** (see H12). A divergence is FAIL, not WARN. Because `metrics_summary` uses two different denominators (`runs` vs `functions_total`, lines 27–28), the checker must carry both — a single-denominator checker would false-pass one of them.

**H7 — Malformed-line count has no source, so "completeness" is vacuous.** The design's completeness gate "forces `rows_malformed_skipped` visible." But `cmd_metrics` (485) drops bad lines with `pass` and **never counts them** — `metrics_summary` only sees survivors. `rows_malformed_skipped` currently has *no producer*; a gate reading it from the survivor-only path always sees `0` and PASSes while data is silently missing.
→ **Check:** the **gather** step is rewritten to be the sole reader and to return `(rows_ok, malformed:[{lineno, raw_prefix, err}], bytes_total)`. `rows_malformed_skipped = len(malformed)`. Completeness gate: `assert manifest.sources[i].rows_total == len(rows_ok)+len(malformed)` **and** the malformed count appears in `render`. Non-zero malformed forces `verdict >= WARN` and a `caveats` entry with line numbers. The count is produced upstream of the gate, so the gate can't be fed a self-serving `0`.

**H8 — trace's blanket `except: continue` silently deletes criteria.** `trace_rows` (52,64,92,114) swallows any per-criterion exception → a malformed criterion produces **no row at all** — not even `(unresolved)`. So `covered + unresolved < len(criteria)` and the missing requirement is invisible. `cmd_trace` returns 0 (line 1611, unresolved==0) on a plan whose criteria were silently eaten.
→ **Check:** faithfulness gate asserts **`covered + unresolved == len(criteria)`** against the *declared* `criteria` list (not against `rows`). A shortfall = FAIL with `criteria_dropped: N`. Additionally, `trace_rows` gather path records a `parse_errors` list (criterion id + exception) rather than `continue`-into-void, and every dropped criterion becomes a synthetic `(unresolved: parse-error)` row so it is *counted* and *rendered*, never vanished.

**H9 — `unresolved==0` reported over an empty/failed load looks like success.** `trace_rows` returns `[]` if `criteria` is falsy or on top-level exception (48, 116); `cmd_trace` then prints "0 unresolved" and returns 0. Zero-of-zero reads as green.
→ **Check:** distinct verdict `EMPTY` (exit 0 but flagged) when `len(criteria)==0`, and `FAIL` when `criteria` declared non-empty but `rows==[]` (total parse failure). PASS requires `len(rows) > 0 and covered+unresolved==len(criteria) and unresolved==0`. `unresolved_surfaced` is a mandatory substantive check (not N/A) for trace mode.

### "Broken ≠ empty" — the registry/pins divergence trap

**H10 — Corrupt registry renders as "no live capabilities" (vacuous clean).** `registry.load` correctly returns `{"__error__":…}` on a broken file — but `cmd_whatis` (682–687) iterates and filters `status=="live"`; the string sentinel is filtered out, so a corrupt `capabilities.json` prints an **empty live list and returns 0**. The exact divergence trap the registry exists to catch is laundered into a clean status.
→ **Check:** gather detects `"__error__" in table` → **REFUSE** (exit 2) with the error surfaced, manifest `verdict:REFUSE`, `refuse_reason:"registry unreadable: …"`. Gate `registry_coherent` is FAIL, never N/A, when the sentinel is present. No-arg whatis additionally runs `registry.audit()` (already checks *every* live/designed canonical exists on disk) and any violation ⇒ WARN with the list — closing H14.

**H11 — Corrupt/missing `.pins.json` masquerades as "not yet built."** `cmd_trace` (1586–1589) `except: pins={}` — an unreadable pins file makes **every** function render `UNPINNED`, indistinguishable from a legitimately-unbuilt plan. A reader concludes "needs building" when the truth is "provenance store is corrupt."
→ **Check:** mirror `registry.load` doctrine — tri-state per source: `absent` (legit empty), `present_empty`, `unreadable` (loud). `sources[pins]` carries `state ∈ {absent,ok,unreadable}` + `err`. `unreadable` ⇒ gate FAIL, `verdict:FAIL`, render stamps `PINS UNREADABLE — UNPINNED counts are NOT trustworthy`. Never silently `{}`.

**H12 — Board error swallowed into a sentinel dict.** `cmd_status` (341–342) sets `counts={"(board error)": str(e)}` and proceeds to PASS. The manifest would record that dict as `board_counts` and a green verdict.
→ **Check:** gather detects a non-integer-valued / sentinel board result → `sources[board].state="error"`, gate FAIL (not N/A), verdict FAIL. A board error is a failed inspection, not a status line.

### Liveness honesty — the 503/loading doctrine

**H13 — `probed_live:true` is a hardcodable literal, and `_probe` calls a loading model "up".** Two sub-holes. (a) The design proves liveness only by "the flag `probed_live:true` exists" — a renderer bug/attacker can emit the literal `true` with zero probing. (b) `_probe` (101–108) returns `"up (503)"` for a model returning 503 *while loading a 20GB weight off HDD* — CLAUDE.md's exact doctrine says that's **loading, not ready**, yet the render says "up". This is misleading in the *opposite* direction the design guards.
→ **Check:** (a) `probed_live` is not a boolean the renderer sets — it is **derived** from a `probe_ts` captured inside the probe function immediately after the socket returns, plus `probe_latency_ms`. The liveness_honesty gate asserts `probe_ts` is within the run's `[ts_started, ts_ended]` window (proves it was probed *this run*, not cached). Absence of `probe_ts` = FAIL. (b) `_probe` returns a **tri-state**: `down` (conn refused), `loading` (HTTP 503 / connect-but-no-body-within-timeout), `ready` (2xx/4xx that isn't 503). The render must print the tri-state verbatim; the gate FAILs if a `loading` probe is rendered as `up/ready`. `liveness_honesty` is a substantive PASS/FAIL for status mode, never N/A.

### Render ↔ manifest divergence

**H14 — no-arg whatis lists a capability whose canonical is missing (already covered in H10 fix).**

**H15 — `render_sha256` proves the render matches *itself*, not the manifest facts.** The design hashes "the rendered block," but `cmd_metrics` prints `"%.0f%%"` (line 491) rounding a float the manifest stores at full precision, and `%.2f` for avg_tries. The sha binds the string to a hash but nothing forces the *printed numbers* to equal `work.found`. A rounding/format bug renders `95%` while the manifest says `0.945`→ reader and record disagree, sha still "valid."
→ **Check:** invert control. The render is **generated by a single serializer from `work.found`** (`render = render_mode(m.work)`), captured to a buffer, `render_sha256 = sha256(buffer)`, buffer is what's written to stdout. The faithfulness gate (H6) compares the *raw* aggregates to the *parsed-back numbers from the render string* at the render's declared precision — so "render says 95%, 0.945 rounds to 95% at 0 dp" is asserted, and a real divergence (95% vs 0.945→ should be 94% or 95%) is caught. render and manifest are provably the same computation, not just the same bytes.

**H16 — source sha256 hashes a re-read, not the parsed bytes (TOCTOU).** Provenance `sha256`/`mtime`/`bytes` computed by re-`open`ing after gather can capture a *different* file than the one parsed (metrics ledger is appended to live by the engine).
→ **Check:** **read-once.** Gather reads the whole file into a `buf`; `sha256(buf)`, `len(buf)`, and the parsed rows all derive from that single `buf`. `mtime` captured via `fstat` on the same open handle. The provenance describes exactly the bytes that produced the numbers.

### Selection / gate-shape vacuity

**H17 — all-N/A "PASS".** The gate lists checks that can each be `N/A` (design's own example: liveness_honesty N/A for metrics, cross_source N/A for single-source). A bug/attacker marking *every* applicable check N/A yields a green verdict with zero substantiated checks.
→ **Check:** a static **`APPLICABLE[subcmd] → {check: required|optional|forbidden}`** table. `metrics.summary` requires `{faithfulness, completeness, freshness}`; `trace` requires `{faithfulness, unresolved_surfaced, cross_source(pin-exists)}`; `status` requires `{liveness_honesty, freshness, board_coherent}`; `whatis` requires `{registry_coherent}`. `finalize` asserts every `required` check has verdict ∈ {PASS,WARN,FAIL} (N/A on a required check = manifest ERROR) and **at least one check is a non-N/A PASS/WARN/FAIL**. An all-N/A gate cannot exist.

**H18 — Selection "why" can be blank and still pass.** The design records selection even when "none," but nothing forces a *reason*; an empty `why:""` satisfies the field.
→ **Check:** `selection.why` must be non-empty and, when `personas==[] and lenses==[]`, must match the canonical string `"read-only deterministic render; no judgment injected"` **and** `intake.thinking_level ∈ {casual,medium}`. Selecting no persona at `high` = ERROR (high *requires* the `data-integrity`+`adversarial` lenses per the design's own table). Selection is checked for coherence with the thinking level, not just presence.

### Freshness / thinking-level

**H19 — `stale` in `sources[]` and the freshness gate use different thresholds → render says fresh, gate says stale (or vice-versa).** Two computations of "stale" drift.
→ **Check:** single constant `FRESH_THRESHOLD_S` (per-source-kind table). `sources[i].stale` and the `freshness` gate both read it; a unit test asserts `source.stale == (gate.freshness != PASS)`. Freshness WARN cannot be silently downgraded — `verdict = max(verdict, WARN)` is applied by the aggregator, not the check author.

**H20 — mtime freshness is forgeable / clock-skew false-fresh.** `touch` on a stale ledger reads fresh; a wrong host clock reads everything fresh.
→ **Check (bounded honesty):** freshness additionally compares the newest **in-content** timestamp (metrics rows carry `ts`; ledger lines are date-named) to mtime; if in-content newest is far older than mtime, render `WARN: mtime newer than content (possibly touched)`. Can't fully close forgery, but the *discrepancy* is surfaced rather than trusted.

**H21 — thinking-level dial silently scales facts, not just scrutiny.** If `high` adds a "per-criterion drift narrative" that the model writes into `work.found`, a model call is now mutating facts — violating "code owns the facts."
→ **Check:** `work.found` is written **only** by deterministic gather; lens output is confined to `caveats[]` and a separate `interpretation[]` block, both structurally forbidden (schema-enforced: `additionalProperties:false` on `work.found`) from altering any numeric field. A grep/AST gate asserts no model-call return value flows into `work` or `gate.checks[].verdict`.

**H22 — empty-metrics `metrics_summary` returns all-zeros → PASS reads as "0% success, verified."** `r==0` branch (8–17) returns zeros; a manifest PASS over no data misleads.
→ **Check:** `verdict:EMPTY` (exit 0, flagged) when `rows_total==0`; render prints `no runs recorded` not `0% success`. Distinct from a real 0%.

---

## PART C — the hardened workflow (implementer's spec)

### Ordered steps (typed) — emission is dispatcher-owned

| # | Phase | Type | Hardened action + guard |
|---|-------|------|--------------------------|
| — | **wrapper** | **AUTO (spine)** | `run_contract` opens `Manifest` (mints collision-proof `run_id` H3, reserves path, `ts_started`), runs handler in `try`, emits in `finally` (H0/H1/H2). No handler exits the process. Grep-gate: no `cmd_*` reachable except via `run_contract` (H0). |
| 0 | Intake | AUTO | Classify `argv[0]`→mode; set thinking level; record `run_context` (`standalone`/`child_of:<id>`, always own file H4). |
| 1 | Front-end | AUTO (no model/write) | Resolve target tri-state (`ok`/`ambiguous`/`missing`), reusing `_resolve_plan`/registry/ledger path. Miss ⇒ **raise `Refuse`** with candidates → manifest `verdict:REFUSE` written by the wrapper (not by an early `return`). |
| 2 | Selection | AUTO + data | casual/medium: `personas:[], why:"read-only deterministic render; no judgment injected"`. high: `data-integrity`+`adversarial` **required** (H18). Coherence-checked against thinking level. |
| 3 | Gather | AUTO | **Sole reader**, read-once into buffers (H16). Returns rows_ok + **malformed[]** (H7), tri-state per source `{absent,ok,unreadable,error}` (H11/H12), registry `__error__` sentinel surfaced (H10), probe tri-state `{ready,loading,down}` with `probe_ts` (H13). Populates `sources[]` + `work.found` (facts only — H21). |
| 4 | Adversarial gate | GATE (deterministic; +lens after) | Runs the `APPLICABLE[mode]` required set (H17). **faithfulness** via independent `FORMULAS` at rendered precision (H6/H15); **completeness** `rows_total==ok+malformed` & malformed rendered (H7); **trace** `covered+unresolved==len(criteria)` (H8/H9); **freshness** single-threshold (H19/H20); **liveness_honesty** `probe_ts` in-window + no `loading`-as-`up` (H13); **registry/board/pins coherence** broken≠empty (H10/H11/H12). Verdict aggregated with `max()` monotonic escalation. Lens runs **after** verdict is set, off critical path (H5/H21) → `caveats[]`/`interpretation[]` only. |
| 5 | Manifest | AUTO — dispatcher `finally` | Serializer builds `render` from `work.found`, `render_sha256=sha256(render)` (H15); schema-validate required fields (H2); atomic write + read-back verify + `O_EXCL` (H1/H3); fallback→stderr (H1). Exit code from verdict. |

### Verdict lattice (exit codes)
`REFUSE`(2) · `ERROR`(3, schema/emit failure) · `FAIL`(1, a required gate FAILed) · `WARN`(0+flag: stale / small-N / malformed-present / mtime-touched) · `EMPTY`(0+flag: zero rows/criteria) · `PASS`(0, ≥1 substantive non-N/A check green). Aggregator applies `verdict = max(...)`; no author can downgrade.

### Manifest — hardened fields (added/changed vs the proposal in **bold**)

```jsonc
{
  "run_id": "20260704T2210Z-a1b2c3d4-8123-9f2e",   // **+pid+nonce (H3)**
  "invocation": "trace-inspect", "subcommand": "...", "argv": [...],
  "ts_started": "...", "ts_ended": "...", "elapsed_ms": 41,
  "timing": {"gather_ms":33,"gate_ms":6,"render_ms":2},
  "intake": {"thinking_level":"medium","mode":"metrics","run_context":"standalone|child_of:<id>"},
  "front_end": {"target_requested":"...","target_resolved":"...","disambiguation":[],
                "refused":false,"refuse_reason":null},
  "selection": {"personas":[],"lenses":[],"why":"read-only deterministic render; no judgment injected"},
  "sources": [
    {"path":"...","kind":"metrics-ledger",
     "state":"ok",                                  // **absent|ok|present_empty|unreadable|error (H11/H12)**
     "err":null,                                    // **loud on broken (H10/H11/H12)**
     "bytes":20481,"mtime":"...","sha256":"...",    // **hash of the read-once buffer (H16)**
     "rows_total":128,"rows_ok":127,
     "rows_malformed_skipped":1,                    // **produced by gather, not survivor path (H7)**
     "malformed":[{"lineno":88,"err":"...","raw_prefix":"..."}],  // **(H7)**
     "content_newest_ts":"...","age_seconds":723,"stale":false}   // **single-threshold w/ gate (H19/H20)**
  ],
  "work": { "found": { /* facts only; additionalProperties:false (H21) */ } },
  "gate": {
    "applicable": {"faithfulness":"required","completeness":"required","freshness":"required",
                   "liveness_honesty":"forbidden","cross_source":"optional"},   // **static table (H17)**
    "verdict": "PASS|WARN|FAIL",
    "checks": [
      {"name":"faithfulness","verdict":"PASS",
       "evidence":"build_success_rate: formula builds_ok/runs=121/128=0.945; render '95%' == round(0.945,0dp) (H6/H15)"},
      {"name":"completeness","verdict":"WARN","evidence":"rows_total 128 == ok 127 + malformed 1; malformed rendered (H7)"},
      {"name":"freshness","verdict":"PASS","evidence":"age 723s < 86400s; content_newest==mtime (H20)"}
    ]
  },
  "probes": [ {"name":"analyst","url":"...","state":"loading",  // **ready|loading|down (H13)**
               "http":503,"probe_ts":"...","probe_latency_ms":4012,
               "probed_live":true} ],                          // **derived from probe_ts, not a literal (H13)**
  "models": [], "models_error": null,                          // **lens failure recorded, off critical path (H5)**
  "cost": {"model_calls":0,"tokens_in":0,"tokens_out":0,"usd":0.0},
  "caveats": [], "interpretation": [],                         // **lens output confined here (H21)**
  "children": [],                                              // **parent<-child cross-ref, never a substitute (H4)**
  "schema_incomplete": [],                                     // **populated => verdict ERROR (H2)**
  "verdict": "PASS",                                           // PASS|WARN|EMPTY|FAIL|REFUSE|ERROR
  "render_sha256": "...",                                      // **sha of serializer output == stdout (H15)**
  "manifest_path": "docs/ce/<run_id>.manifest.json"
}
```

### Mode-specific required gate checks (the anti-vacuity table, H17)
- **trace:** `faithfulness` (covered+unresolved==len(criteria), H8/H9) · `unresolved_surfaced` (required, non-hideable) · `cross_source` (every rendered pin sha exists in `.pins.json`; pins `state==unreadable`⇒FAIL, H11).
- **metrics:** `faithfulness` (FORMULAS, both denominators, H6) · `completeness` (malformed surfaced, H7) · `freshness` (H19/H20). `EMPTY` when 0 rows (H22).
- **status:** `liveness_honesty` (probe_ts in-window; loading≠up, H13) · `board_coherent` (no sentinel, board count vs `.pins.json` count, H12) · `freshness` (ledger tail).
- **whatis:** `registry_coherent` (`__error__`⇒REFUSE; no-arg ⇒ `registry.audit()` over all live canonicals, H10/H14).

### Load-bearing invariants a reviewer must be able to grep for
1. Exactly one process-exit, inside `run_contract`'s `finally`.
2. No `cmd_*` invoked except through `run_contract` (internal callers pass `parent_ctx`).
3. `work.found` numeric fields are assigned only in `gather`; no lens/model return value flows into `work` or `gate.checks[].verdict`.
4. Every source read exactly once; sha/bytes/rows derive from the same buffer.
5. `render` is produced by the serializer from `work.found`; the bytes hashed into `render_sha256` are the bytes sent to stdout.
6. `broken != empty` for all three stores (registry sentinel, pins tri-state, board sentinel) — each maps to FAIL/REFUSE, never a clean zero.

The canonical proof the design wants — "even `lathe status` routes through the contract, 0 models, <50ms" — holds only with H0 (dispatcher-owned emission) and H17 (no all-N/A pass) in place. Without those two, the cheapest command is exactly the one that quietly runs around the spine.