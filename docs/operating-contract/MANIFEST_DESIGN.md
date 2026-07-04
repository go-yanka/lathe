I have everything I need: the dispatcher (`lathe.py:1687` `main()`), the token accounting (`engine_v2.py:252` `tok` dict), the confirmed analyst-token gap (`claude_proxy.py:189` hardcodes `usage: {0,0,0}`; `engine_v2.py:287` never reads usage on the claude branch; `engine_v2.py:1145` literally says "ANALYST … NOT INSTRUMENTED"), the existing per-build metrics record (`metrics/runs.jsonl`), and current Claude pricing. Here is the implementation-ready design.

---

# Lathe Per-Invocation MANIFEST — Full Design

The manifest is the evaluation instrument for the operating contract. It is phase 5 of the six-phase spine and is emitted by deterministic code for **every** invocation — pass, refuse, or crash. This design is grounded in the real code: the single dispatcher chokepoint is `main(argv)` at `lathe.py:1687` (subcommand `table` at `:1694`, bare-goal fallthrough `cmd_do(argv)` at `:1707`); token state lives in the module-global `tok = {"p":0,"e":0,"claude_calls":0}` at `engine_v2.py:252`; the existing per-build record is written to `metrics/runs.jsonl` at `engine_v2.py:1191`.

---

## 1. The exact JSON schema

One manifest object per invocation, written to `docs/ce/<run_id>.manifest.json`. `schema_version` is frozen; consumers pin to it. Every field is present on every emission (nulls, not omissions) so acceptance tests can assert structural completeness. Times are ISO-8601; durations are seconds (float); costs are USD (float, 6-dp).

```json
{
  "schema_version": "1.0.0",
  "manifest_id": "cem_20260704-131502-a1b9",
  "run_id": "20260704-131502-a1b9",
  "parent_run_id": null,

  "invocation": {
    "argv": ["do", "parse a duration like '2h30m' into seconds"],
    "command": "do",
    "resolved_command": "do",
    "routed_via": "table",
    "is_bare_goal": false,
    "goal_raw": "parse a duration like '2h30m' into seconds",
    "cwd": "/home/user/proj",
    "pid": 48213,
    "invoked_by": "cli",
    "lathe_version": "2.9.0",
    "git_sha": "07bbd6a",
    "config_hash": "sha256:5f2c…",
    "strict": true,
    "env_snapshot": {
      "LATHE_STRICT": "1",
      "LATHE_MODEL": "openai:local",
      "LATHE_TRIES": "3",
      "LATHE_THINK": "medium"
    }
  },

  "intake": {
    "invocation_type": "build-from-goal",
    "skill": "workflows/do",
    "workflow_steps": ["clarify","assumption-audit","analyst-plan","spec-lint",
                       "generate","strict-gates","adversarial-synth","pin","regression","manifest"],
    "thinking_level": "medium",
    "thinking_resolved": {"personas": 3, "tries": 3, "adversarial": "thorough", "select_n": 3},
    "goal": "parse a duration like '2h30m' into seconds",
    "goal_source": "argv",
    "run_started_at": "2026-07-04T13:15:02Z"
  },

  "front_end": {
    "ran": true,
    "clarify": {
      "ran": true,
      "questions": [
        {"q": "Should a bare number be treated as seconds?", "answer": "yes", "source": "assumed"}
      ],
      "brief_path": "docs/ce/20260704-131502-a1b9.clarified.md"
    },
    "assumptions": [
      {"id": "A1", "text": "negative durations are rejected", "materiality": "high",
       "resolution": "stated-intent", "blocking": false}
    ]
  },

  "selection": {
    "selector": {"mode": "grade-weighted", "explore_exploit": "exploit",
                 "seed": 1751633702, "candidate_pool_size": 27, "degraded": false},
    "personas": [
      {"id": "reliability-engineer", "role": "implementer-lens", "grade": 0.86,
       "why": "goal parses untrusted string input; edge-case density high", "selected_by": "decider"}
    ],
    "lenses": ["input-validation", "overflow-safety"]
  },

  "contributors": [
    {
      "id": "analyst",
      "role": "spec+test author",
      "kind": "model",
      "phase": "work",
      "action": "authored spec + 9 itests for parse_duration",
      "model": "claude:sonnet",
      "thinking_level": "medium",
      "started_at": "2026-07-04T13:15:03Z",
      "ended_at": "2026-07-04T13:15:41Z",
      "elapsed_s": 38.2,
      "calls": 2,
      "tokens": {"prompt": 4120, "completion": 2310, "total": 6430,
                 "cache_read": 0, "cache_write": 0, "source": "measured"},
      "cost_usd": 0.078350,
      "findings": [
        {"kind": "spec", "verbatim": "parse_duration('2h30m') == 9000; reject '' -> ValueError",
         "artifact": "docs/ce/…/plan.py"}
      ],
      "status": "ok"
    },
    {
      "id": "implementer",
      "role": "code author",
      "kind": "model",
      "phase": "work",
      "action": "generated parse_duration under gates (best-of-3)",
      "model": "openai:local",
      "thinking_level": null,
      "started_at": "2026-07-04T13:15:41Z",
      "ended_at": "2026-07-04T13:16:12Z",
      "elapsed_s": 31.0,
      "calls": 3,
      "tokens": {"prompt": 1802, "completion": 640, "total": 2442,
                 "cache_read": 0, "cache_write": 0, "source": "measured"},
      "cost_usd": 0.0,
      "findings": [{"kind": "impl", "verbatim": "passed 9/9 itests on try 2", "artifact": "…/module.py"}],
      "status": "ok"
    }
  ],

  "work": {
    "steps": [
      {"id": "analyst-plan", "type": "you", "name": "analyst writes plan", "status": "pass",
       "detail": "1 function, 9 itests", "started_at": "…", "ended_at": "…", "elapsed_s": 38.2},
      {"id": "generate", "type": "auto", "name": "generate under gates", "status": "pass",
       "detail": "parse_duration: pass (try 2 of 3)", "elapsed_s": 31.0}
    ]
  },

  "gates": {
    "all_pass": true,
    "verdicts": [
      {"gate": "spec-lint", "verdict": "pass", "blocking": true,
       "detail": "tests pin behavior; 0 mutation survivors", "evidence": "…/spec_lint.json"},
      {"gate": "strict-gates", "verdict": "pass", "blocking": true, "detail": "regression-proof, test-ack, test-kind all green"},
      {"gate": "adversarial-synth", "verdict": "pass", "blocking": true,
       "detail": "6 adversarial cases generated; all pass", "evidence": "…/adversarial.json"},
      {"gate": "standing-regression", "verdict": "pass", "blocking": true, "detail": "module_ok"}
    ]
  },

  "models": [
    {"alias": "analyst", "provider": "claude-cli-proxy", "model_id": "claude-sonnet-5",
     "endpoint": "http://127.0.0.1:8787/v1/chat/completions", "billing_mode": "subscription",
     "calls": 2, "tokens": {"prompt": 4120, "completion": 2310, "total": 6430},
     "cost_usd": 0.0, "imputed_cost_usd": 0.078350},
    {"alias": "implementer", "provider": "openai-local", "model_id": "local",
     "endpoint": "http://127.0.0.1:8089/v1/chat/completions", "billing_mode": "local-free",
     "calls": 3, "tokens": {"prompt": 1802, "completion": 640, "total": 2442},
     "cost_usd": 0.0, "imputed_cost_usd": 0.0}
  ],

  "usage": {
    "tokens": {
      "prompt": 5922, "completion": 2950, "total": 8872,
      "by_role": {
        "analyst":     {"prompt": 4120, "completion": 2310, "total": 6430, "source": "measured"},
        "implementer": {"prompt": 1802, "completion": 640,  "total": 2442, "source": "measured"},
        "judge":       {"prompt": 0,    "completion": 0,    "total": 0,    "source": "n/a"}
      },
      "completeness": {"all_calls_attributed": true, "uninstrumented_calls": 0}
    },
    "cost_usd": {
      "total": 0.0,
      "imputed_total": 0.078350,
      "by_role": {"analyst": 0.0, "implementer": 0.0, "judge": 0.0},
      "imputed_by_role": {"analyst": 0.078350, "implementer": 0.0, "judge": 0.0}
    },
    "calls": {"total": 5, "analyst": 2, "implementer": 3, "judge": 0},
    "pricebook_version": "2026-06-24"
  },

  "timing": {
    "started_at": "2026-07-04T13:15:02Z",
    "ended_at": "2026-07-04T13:16:14Z",
    "elapsed_s": 72.4,
    "by_phase": {"intake": 0.1, "front_end": 4.2, "selection": 1.1,
                 "work": 62.0, "adversarial_gate": 4.0, "manifest": 0.2}
  },

  "outcome": {
    "status": "pass",
    "reason": "all gates green; 1/1 functions pinned",
    "exit_code": 0,
    "refused": false,
    "error": null,
    "artifacts": ["…/module.py", "…/itest.py", "…/.pins.json"],
    "pins": [{"function": "parse_duration", "pin": "sha256:9ab4…", "source": "generated"}]
  },

  "integrity": {
    "emitted_by": "dispatcher.finalize",
    "emitter_version": "1.0.0",
    "manifest_sha256": "sha256:<hash of the object with this field blanked>",
    "partial": false
  }
}
```

**Field-group rationale (why each exists):**

- `invocation` — reproducibility: exact argv, whether it came in as a bare goal (`is_bare_goal`/`routed_via` prove the bare command was routed *through* the contract, not around it), the code/config version, and the env that shaped behavior.
- `intake` / `front_end` / `selection` — the "who/what/why" the evaluation cares about: the resolved workflow, the thinking level and what it expanded to, the clarify Q&A, the assumptions with materiality, and **personas/lenses with a `why` string per pick** plus the selector mechanics (seed makes selection reproducible; `degraded` flags a down decider).
- `contributors[]` — one row per actor (analyst, implementer, judge, each gate, each persona) with **verbatim findings** (`findings[].verbatim` is the literal spec text / review finding / adversarial case, never a paraphrase), per-contributor tokens+cost+timing, and `status`.
- `gates` — every gate verdict with `blocking` and machine-readable `evidence` pointers; `all_pass` is the single boolean the spine checks.
- `models` / `usage` — dollar cost **and** tokens, split by role, with `billing_mode` distinguishing subscription (marginal $0 but non-zero `imputed_cost_usd` at list price) from metered. `completeness.all_calls_attributed` is the field that makes the analyst-token gap *visible and testable*.
- `outcome` — the terminal verdict (`pass` / `refuse` / `error`), exit code, artifacts, pins.
- `integrity` — `manifest_sha256` (self-hash) + `partial` flag so a crash-time manifest is recognizable as such.

---

## 2. Human-readable render

`docs/ce/<run_id>.manifest.md`, generated deterministically from the JSON by the same finalizer (never authored by a model). Fixed-order sections so it diffs cleanly across runs:

```
LATHE RUN MANIFEST — 20260704-131502-a1b9                         PASS ✓
────────────────────────────────────────────────────────────────────────
INTAKE     do "parse a duration like '2h30m' into seconds"
           type=build-from-goal   thinking=medium   strict=ON
           lathe 2.9.0 @07bbd6a   config 5f2c…

FRONT-END  clarify: 1 Q (assumed) → bare number = seconds
           assumptions: A1 reject negatives [high] → stated-intent (non-blocking)

SELECTION  personas (grade-weighted, exploit, seed 1751633702):
           • reliability-engineer  0.86  — untrusted string input, high edge-case density
           lenses: input-validation, overflow-safety

CONTRIBUTORS
  analyst      claude:sonnet   38.2s   2 calls   6,430 tok   $0.00 ($0.078 list)
    └ spec: parse_duration('2h30m')==9000; reject '' -> ValueError   (9 itests)
  implementer  openai:local    31.0s   3 calls   2,442 tok   $0.00
    └ passed 9/9 itests on try 2

GATES      spec-lint ✓   strict-gates ✓   adversarial-synth ✓ (6 cases)   regression ✓

USAGE      tokens 8,872 (analyst 6,430 · impl 2,442 · judge 0)   attribution: COMPLETE
           cost $0.00 real / $0.078 imputed        pricebook 2026-06-24
TIMING     72.4s total   (work 62.0 · front-end 4.2 · adv-gate 4.0)

OUTCOME    PASS — all gates green; parse_duration pinned (9ab4…)
           artifacts: module.py, itest.py, .pins.json
────────────────────────────────────────────────────────────────────────
manifest sha256:… · emitter 1.0.0
```

A `REFUSE`/`ERROR` render uses the identical skeleton; the banner flips, the `OUTCOME` block carries the reason/error, and any phase not reached prints `— not reached —` rather than being omitted (so the render itself testifies to where it stopped).

---

## 3. Making emission non-optional (where, in deterministic code)

The guarantee is structural: the dispatcher, not any skill, owns emission. Wrap the single chokepoint.

**Today** `lathe.py:1687`:
```python
def main(argv):
    ...
    if cmd in table:
        return table[cmd](rest)
    return cmd_do(argv)          # bare goal
```
Two exits, and `cmd_*` can `return` or `raise` — either path can skip a record. Replace both exits with a wrapper that emits in a `finally`, so **no return, no raise, and no `sys.exit` inside a handler can escape without a manifest**:

```python
def main(argv):
    os.environ["LATHE_VALIDATE_PLAN"] = "1"
    ...
    if not argv or argv[0] in ("help","-h","--help"):
        print(__doc__); return 0
    cmd, rest = argv[0], argv[1:]
    handler, routed = (table[cmd], "table") if cmd in table else (lambda _r: cmd_do(argv), "bare-goal")

    mf = Manifest.begin(argv=argv, command=cmd, routed_via=routed)   # phase 0: opens the record NOW
    ctx.MANIFEST = mf            # contributors/gates append into this during the run
    try:
        rc = handler(rest)
        mf.set_outcome(status="pass" if rc == 0 else "refuse", exit_code=rc)
        return rc
    except SystemExit as e:                       # a handler called sys.exit()
        mf.set_outcome(status="refuse" if e.code else "pass", exit_code=e.code or 0); raise
    except BaseException as e:                     # crash, KeyboardInterrupt, gate abort
        mf.set_outcome(status="error", exit_code=1, error=repr(e)); raise
    finally:
        mf.finalize()            # phase 5: ALWAYS writes docs/ce/<run_id>.manifest.{json,md}
```

Enforcement properties:

1. **Single chokepoint.** Every subcommand and the bare-goal path go through this one function (already true: `table` + fallthrough). Bare `lathe "<goal>"` is routed here and stamped `routed_via:"bare-goal"` — it runs *through* the contract, provably.
2. **`finally` is unconditional.** Success, `return != 0`, `SystemExit`, gate `raise`, `KeyboardInterrupt` — all pass through `finalize()`. A handler cannot suppress it.
3. **`begin()` first, `finalize()` last.** The record opens in phase 0 before any work; if the process is killed mid-run, `begin()` has already written a `partial:true` stub to disk (atomic temp-rename, same `_atomic_write` pattern at `engine_v2.py:245`), which `finalize()` overwrites on clean exit. A missing manifest therefore means "process hard-killed before phase 0," which itself is detectable (see test 6).
4. **Skills cannot disable it.** Skills/workflows only *append* to `ctx.MANIFEST` (contributors, gate verdicts, findings). They have no handle to skip `finalize()` — it is bound in `main`, above the skill layer. This is the code/skill split: the record is code; its *content* is skill.
5. **The engine feeds, doesn't own.** `engine_v2.py`'s existing `metrics/runs.jsonl` write (`:1191`) becomes one *contributor's* data merged into the manifest, not the record of truth. A build launched inside `do` reports its `tok`/gates up into `ctx.MANIFEST`; the manifest is emitted once per *invocation* even when the invocation runs many builds (each build also keeps its row for backward compat).

`Manifest` is a small deterministic module (`projects/agentic-harness/tools/manifest.py`) — `begin/append_contributor/record_gate/set_selection/set_outcome/finalize`. No model calls. Pure assembly + atomic write + self-hash.

---

## 4. Closing the analyst-token gap

The gap is real and has three distinct layers, all confirmed in the code:

- **L1 — the proxy emits zeros.** `claude_proxy.py:189` hardcodes `"usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}` on the non-stream path. The Claude CLI's own token counts are never surfaced.
- **L2 — the engine wouldn't read them anyway.** `engine_v2.py:287`, the `model=="claude"` branch, only does `tok["claude_calls"] += 1` and returns content — it never touches `d.get("usage")` (contrast the `openai:` branch at `:302` which does).
- **L3 — no role attribution.** `tok` at `:252` is one flat `{"p","e"}` bucket. Even with counts, analyst vs implementer vs judge can't be separated, and there's no dollar cost anywhere. The RUN_REPORT literally admits it: `"ANALYST … NOT INSTRUMENTED this run"` (`:1145`).

**Fix, layer by layer:**

**L1 — make the proxy report real usage.** The Claude CLI `--output-format json` (and the `stream-json` result event already used at `:193`) emits a final `usage`/`result` object carrying `input_tokens` / `output_tokens` (and cache tokens). In `claude_proxy.py`, switch the non-stream `_run()` to `--output-format json`, parse the trailing result object, and populate real usage instead of zeros:

```python
# claude_proxy.py, non-stream branch (~:184)
u = _parse_cli_usage(r.stdout)   # reads the CLI result event: input_tokens/output_tokens/cache_*
return JSONResponse({ ...,
    "usage": {"prompt_tokens": u["input"], "completion_tokens": u["output"],
              "total_tokens": u["input"] + u["output"],
              "cache_read_input_tokens": u.get("cache_read", 0),
              "cache_creation_input_tokens": u.get("cache_write", 0),
              "token_source": "measured"}})
```
If the CLI build doesn't surface usage, fall back to `client.messages.count_tokens(model=…)` on prompt and completion and tag `token_source:"estimated"` — never silently zero.

**L2 — read usage on the claude branch and attribute by role.** Thread a `role` through the call path and split `tok` into role buckets:

```python
# engine_v2.py
tok = {"analyst":    {"p":0,"e":0,"cr":0,"cw":0,"calls":0,"src":"n/a"},
       "implementer":{"p":0,"e":0,"cr":0,"cw":0,"calls":0,"src":"n/a"},
       "judge":      {"p":0,"e":0,"cr":0,"cw":0,"calls":0,"src":"n/a"}}

def call_model(prompt, temperature, model, role="implementer"):   # role added
    ...

# claude branch (~:287) now mirrors the openai branch:
u = d.get("usage") or {}
b = tok[role]
b["p"] += u.get("prompt_tokens", 0); b["e"] += u.get("completion_tokens", 0)
b["cr"] += u.get("cache_read_input_tokens", 0); b["cw"] += u.get("cache_creation_input_tokens", 0)
b["calls"] += 1; b["src"] = u.get("token_source", "measured")
```
Every analyst call site (spec/test authoring — e.g. `call_model(jp, 0.0, "claude")` at `:422`) passes `role="analyst"`; the judge path passes `role="judge"`; generation passes `role="implementer"`. `claude_calls` is retained as `analyst.calls + judge.calls` for backward compat with existing `runs.jsonl` consumers.

**L3 — dollars + completeness.** A pricebook maps `model_id → {input_per_mtok, output_per_mtok, billing_mode}`, versioned (`pricebook_version`), current values from the model catalog: `claude-opus-4-8` $5.00/$25.00, `claude-sonnet-5` $3.00/$15.00, `claude-haiku-4-5` $1.00/$5.00 per 1M tokens (cache reads ~0.1×, writes ~1.25× applied to `cache_*`). For a subscription proxy the real `cost_usd` is `0.0` but `imputed_cost_usd = tokens × list-price` is computed and recorded so savings are measurable — which is exactly what `:1146` asks for ("to measure true savings, automate the analyst … and sum its tokens here").

The **completeness invariant** makes the gap un-hideable going forward: the manifest computes `completeness.all_calls_attributed = (sum of per-role calls == total model calls observed)` and `uninstrumented_calls`. If any call lands in a bucket with `src:"n/a"` while `calls>0`, or a role reports `calls>0` with `total==0` tokens, the finalizer sets `all_calls_attributed=false` and the manifest ships with the discrepancy visible (rather than a silent zero). Acceptance test 4 fails on exactly that condition.

---

## 5. Acceptance tests (prove complete + un-skippable)

These are executable probes in the same style as the gate stress-tests. Each drives a real invocation and asserts on the emitted manifest.

**T1 — Emission is universal.** For every command in the dispatcher `table` (`lathe.py:1694`) plus the bare-goal form, run it (using a stub model where needed) and assert `docs/ce/<run_id>.manifest.json` exists and parses. *Proves phase 5 fires for all ~35 entry points, not just `do/build/auto`.*

**T2 — Un-skippable under failure.** Force each terminal path: (a) a handler that `return 2`; (b) a handler that `raise RuntimeError`; (c) a gate that aborts; (d) `SystemExit(3)`; (e) SIGINT mid-run. After each, assert a manifest exists and `outcome.status` ∈ {`refuse`,`error`} with the right `exit_code`. *Proves the `finally` in `main` cannot be bypassed by return, raise, exit, or interrupt.*

**T3 — Structural completeness.** JSON-Schema-validate every emitted manifest against the frozen `schema_version` schema: all top-level groups present, no field null-where-forbidden, `contributors[]` non-empty for any invocation that made ≥1 model call, every `gates.verdicts[]` entry carries `verdict`+`blocking`. *Proves the record captures goal, selection+why, contributors, gate verdicts, thinking, models, tokens+cost, timing, outcome — the required inventory.*

**T4 — Analyst tokens are instrumented (the gap is closed).** Run a `do` that forces ≥1 analyst (claude-proxy) call. Assert `usage.tokens.by_role.analyst.total > 0`, `.source == "measured"`, `usage.completeness.all_calls_attributed == true`, and `usage.calls.analyst == models[analyst].calls`. Regression-lock: assert the manifest **never** contains the string "NOT INSTRUMENTED". *Directly proves L1–L3 are fixed and can't silently regress.*

**T5 — Cost is present and role-split.** With a known pricebook and a fixed token count injected, assert `usage.cost_usd.imputed_by_role.analyst == analyst_tokens × list_price` to 6dp, `models[].billing_mode` set, real `cost_usd == 0` for subscription/local while `imputed_cost_usd > 0` for the analyst. *Proves dollar cost, not just tokens, and that subscription $0 is distinguished from missing data.*

**T6 — Bare command routes through the contract.** Run `lathe "<goal>"` (no subcommand) and assert `invocation.routed_via == "bare-goal"`, `is_bare_goal == true`, and a full manifest with `intake.workflow_steps` ending in `"manifest"`. *Proves bare commands go through their contract, not around it.*

**T7 — Verbatim findings, not paraphrase.** Run a `review` (or `do`) and assert each `contributors[].findings[].verbatim` string byte-matches the corresponding artifact/spec/adversarial-case on disk (hash compare). *Proves findings are recorded verbatim, as the evaluation instrument requires.*

**T8 — Determinism / integrity.** Re-run a fully-pinned `build` twice (0 model calls). Assert both manifests are byte-identical after masking the volatile fields (`run_id`, timestamps, `elapsed_s`, pid), and that `integrity.manifest_sha256` recomputes correctly (self-hash with the field blanked). *Proves the record is reproducible and tamper-evident, matching Lathe's determinism thesis.*

T2, T4, and T6 are the load-bearing three: un-skippable, gap-closed, and routed-through-contract.

---

### Files this touches (implementation map)

- `lathe.py:1687` `main()` — wrap dispatch in `Manifest.begin/…/finalize` (§3).
- `projects/agentic-harness/tools/manifest.py` — **new** deterministic assembler/writer (§1–2).
- `projects/agentic-harness/tools/pricebook.py` — **new** versioned model→price table (§4/L3).
- `claude_proxy.py:184–190` — emit real CLI usage instead of hardcoded zeros (§4/L1).
- `engine_v2.py:252` (`tok`), `:260` (`call_model` role param), `:287` (claude branch reads usage), analyst call sites (`:422` etc.), `:1145` (RUN_REPORT), `:1161` (metrics feed up into manifest) (§4/L2–L3).
- `docs/ce/` — output dir for `<run_id>.manifest.{json,md}` (+ `partial` stubs).