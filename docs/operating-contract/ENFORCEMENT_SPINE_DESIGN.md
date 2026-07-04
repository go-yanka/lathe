I have enough to produce the design. Key facts I've grounded it in: `main(argv)` (line 1687) is the single dispatch choke point; `cmd_flow` already re-enters `main()` for AUTO steps (line 943); line 1688 already uses the "FORCE, not setdefault, so a hostile env var can't disable" pattern; `_apply_config_env` already threads `LATHE_TRIES` and `LATHE_ASSUMPTION_POLICY`; `flow_report.classify_step/workflow_verdict` already turn rc into pass/blocked; structured per-run logs already carry a `run_id`.

Here is the implementation-ready design.

---

# Lathe Enforcement Spine (flow-runner) — implementation-ready design

The whole design hangs on one existing fact: **`main(argv)` in `lathe.py:1687` is the only way any command runs, and it is also the only in-process re-entry point (the flow-runner calls `main()` per AUTO step at line 943).** That makes it the single choke point where the spine is installed. Nothing routes around `main`.

## (1) The minimal change — promote flow to the default path

Split the current `main` into a public **spine** and a private **raw dispatch**, gated by a re-entrancy token. This is ~40 lines in `lathe.py` plus one new pinned tool `tools/spine.py`.

**Step A — rename the current dispatch body to a private function.** The body of today's `main` (lines 1693–1707, the `table = {...}` lookup and bare-goal fallthrough) becomes:

```python
def _dispatch(cmd, rest, argv):
    table = { ... }                      # unchanged
    if cmd in table:
        return table[cmd](rest)
    return cmd_do(argv)                  # bare `lathe "<goal>"`
```

**Step B — `main` becomes the spine entry with a re-entrancy guard:**

```python
_SPINE_GUARD = "_LATHE_SPINE_RUN"

def main(argv):
    os.environ["LATHE_VALIDATE_PLAN"] = "1"                 # (existing, keep)
    os.environ["LATHE_VALIDATOR_PY"] = os.path.join(TOOLS, "plan_validator.py")
    _apply_config_env(_lathe_config())
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(__doc__); return 0
    cmd, rest = argv[0], argv[1:]
    if os.environ.get(_SPINE_GUARD):                        # RE-ENTRANT inner step:
        return _dispatch(cmd, rest, argv)                   #   outer spine already owns the contract
    return run_spine(cmd, rest, argv)                       # TOP-LEVEL: the enforced contract
```

**Step C — the process entry FORCE-clears the guard** (identical rationale to line 1688's forced `LATHE_VALIDATE_PLAN`), so a stale or hostile pre-set env var can never trick the top-level call into thinking it is a re-entrant inner step and skipping the contract:

```python
def _cli():
    os.environ.pop(_SPINE_GUARD, None)          # a hostile/inherited guard must not disable the spine
    sys.exit(main(sys.argv[1:]))
```

(Same one-line clear under `if __name__ == "__main__"`.)

**Step D — `run_spine` (new, in `tools/spine.py`, harness-built + pinned):**

```python
def run_spine(cmd, rest, argv):
    run_id = new_run_id()                                   # reuse run_logger's id scheme
    m = Manifest(run_id, argv)                              # phase-5 record object
    try:
        os.environ[_SPINE_GUARD] = run_id                  # from here, inner main() calls run RAW
        c = CONTRACT_FOR.get(cmd, TRIVIAL)                 # DATA: command -> contract
        think = resolve_thinking(c)                        # phase 0: intake
        apply_depth(think)                                 # stamp LATHE_TRIES / SELECT_N / ASSUMPTION_POLICY
        m.intake(cmd, rest, c, think)

        if c.get("front_end"):                             # phase 1: clarify/assume (gated)
            rc = _phase_frontend(c, rest, m)
            if rc: return m.finish(rc, refuse="front-end gate")
        if c.get("select"):                                # phase 2: personas/lenses + WHY
            m.selection(_phase_select(c, rest))

        rc = _phase_work(cmd, rest, c, m)                  # phase 3: the workflow, or the primitive

        if c.get("gate") and rc == 0:                      # phase 4: adversarial + standing gates
            rc = _phase_adversarial(c, rest, m)
        return m.finish(rc)
    except BaseException as e:
        m.error(e); raise
    finally:
        os.environ.pop(_SPINE_GUARD, None)
        m.emit()                                           # phase 5: ALWAYS — even on crash/SystemExit
```

**Step E — `_phase_work` reuses the existing flow-runner.** Factor the step-loop out of `cmd_flow` (lines 927–951) into `_run_workflow(wf, tgt, m)`. If the contract names a workflow, run it; otherwise run the primitive unchanged:

```python
def _phase_work(cmd, rest, c, m):
    wf = get_workflow(c["workflow"]) if c.get("workflow") else None
    if wf:
        return _run_workflow(wf, bind_target(c, rest), m)  # each AUTO step re-enters main() -> RAW
    return _dispatch(cmd, rest, [cmd] + rest)              # no workflow: identical to today + a manifest
```

That is the entire promotion. Bare `lathe review foo.py` now enters `run_spine` → resolves the `code-review` workflow → `_run_workflow` → its first AUTO step `review auto foo.py` re-enters `main()`, sees the guard, and runs the **raw** persona review. The bare command *is* the contract; the primitive it always used is now one gated step inside it.

## (2) What is code vs data vs gated-model-judgment

| Concern | Layer | Where |
|---|---|---|
| Six-phase ordering; re-entrancy guard; `finally`-emit; verdict from rc; depth stamping | **deterministic code** (non-bypassable) | `main`, `run_spine`, `apply_depth` |
| `CONTRACT_FOR` (command→contract), `WORKFLOWS` (steps), persona catalog, thinking-depth table, assumption-policy levels | **data** (auditable, editable, cannot remove a phase) | `workflows.py`, `catalog.json` |
| Persona selection *mechanics* (grade-weight, explore/exploit) | **code** (deterministic given inputs) | `agent_router.py` |
| Clarify questions, assumption audit, analyst spec+tests, persona review bodies, adversarial case synthesis | **skill + model, OUTPUT gated** | AUTO/YOU steps; gated by tests-pass / RTM-green / HIGH-assumption-resolved / mutation-score |

Litmus (already in the design doc): if skipping it must be *impossible*, it is code; if it needs a brain, it is a skill whose output code gates. The phases (0/4/5) live in code **around** the data — a workflow list can define bad steps but cannot delete a phase, because phases are not in the list.

`CONTRACT_FOR` is the new data map (starter set, ~19 rows):

```python
CONTRACT_FOR = {
  "do":     {"workflow":"build-from-goal", "front_end":1, "select":1, "gate":1, "writes":1, "argmap":"goal"},
  "build":  {"workflow":"build-from-plan", "front_end":1, "select":0, "gate":1, "writes":1, "argmap":"plan"},
  "review": {"workflow":"code-review",     "front_end":0, "select":1, "gate":1, "writes":0, "argmap":"files"},
  "sdlc":   {"workflow":"sdlc",            "front_end":1, "select":1, "gate":1, "writes":1, "argmap":"goal"},
  "assume": {"workflow":"assume",          "front_end":0, "select":0, "gate":1, "writes":1, "argmap":"plan"},
  "verify": {"gate":1, "writes":0, "argmap":"plan"},           # gate-only, no workflow
  "gate":   {"gate":1, "writes":0},
  # read-only -> TRIVIAL: run_id + manifest, phases 1/2/4 no-op:
  "status":{}, "logs":{}, "metrics":{}, "board":{}, "plans":{}, "whatis":{}, "trace":{},
}
TRIVIAL = {}
```

`argmap` is how intake binds the bare command's argv onto the workflow's `{plan}`/`{files}`/`{goal}` placeholders — the piece that lets a bare command feed its own workflow.

## (3) Why step-order, gate pass/fail, and manifest can't be disabled by a skill

Three independent code mechanisms, none reachable from data/model:

- **Order + halt:** `_run_workflow` iterates `wf["steps"]` in list order and stops on the first `blocked` (today's lines 947–948). A step's action is executed only by re-entering `main()→_dispatch`; there is no primitive that lets a later step run before an earlier one, and a skill cannot mutate the already-loaded list mid-run.
- **Gate pass/fail:** verdicts come from `classify_step(kind, rc, out)` / `workflow_verdict` (pinned `flow_report.py`) and from the phase-4 gate *process* rc — **not from model text**. A gate is a real subprocess (`run_gates.py`, `hreview`); a skill can emit "looks good" all it wants, but the rc decides, and a nonzero rc → `blocked` → `BLOCKED`/`REFUSE`. Adversarial red flips the spine verdict even if Work returned 0.
- **Manifest:** `finally: m.emit()` runs on success, on `blocked`, on raised exception, and on `SystemExit` (which `finally` catches). The manifest is therefore *unconditional*; a crashed spine still writes a partial record marked `incomplete`, so the **absence** of a manifest is itself a detectable failure.

Why a skill is structurally powerless: a skill is data + model text consumed **inside phase 3**. It never calls `run_spine`, never sets/reads `_SPINE_GUARD` (cleared at process entry, set only by code for the dynamic extent), never touches the `finally`. Its only lever is the content of its steps — which still run gated and still get a manifest. And a skill that **shells out** to `lathe` gets a *fresh* process where the guard is cleared → that child runs its **own** full spine + manifest. There is exactly one raw path — importing the underscore-private `_dispatch` in-process — which only trusted harness code (the flow-runner, under a guard the spine set) ever takes.

## (4) Thinking level → depth

One dial — `LATHE_THINK ∈ {casual, medium(default), high}` (or `--think=high`, or config `thinking.level`) — resolved at intake into a **data** depth table that code stamps into the env for the whole run:

| dial | LATHE_TRIES | select:N | LATHE_ASSUMPTION_POLICY | front-end | adversarial | STRICT (writes) |
|---|---|---|---|---|---|---|
| casual | 1 | 1 | off / high-only non-blocking | skip clarify | smoke | no |
| medium | 3 | 2 | high (blocks) | 1 clarify pass | standard synth | no |
| high | 5 | 4–5 parallel | high+med (blocks) | multi-interviewer | maximal + mutation-forced | yes |

`apply_depth` writes `LATHE_TRIES`, a new `LATHE_SELECT_N` (read by phase-2 selection / `agent_router`), and `LATHE_ASSUMPTION_POLICY` — the last is **already** consumed end-to-end (`_apply_config_env`, line 1679). **Precedence uses the existing `setdefault` pattern (env > profile > config > default):** a user who exported `LATHE_TRIES=7` keeps 7 even at `casual`; the dial only fills what the operator left unset. All code reading a data table — zero model involvement, so the depth mapping is itself a guarantee.

## (5) Backwards-compat + the stress test

**Compat guarantees:**
1. **Primitive stdout + exit code preserved.** Phase 3 ends by running the same command/engine as today; the manifest is a durable **side-file** (`docs/ce/<run_id>.manifest.json`), never mixed into stdout. `lathe build --json`'s metrics block passes through untouched → CI unaffected.
2. **Read-only commands map to `TRIVIAL`:** spine runs (run_id + manifest) but phases 1/2/4 are no-ops → byte-identical behavior, negligible overhead.
3. **`lathe flow` still works** — it now runs *under* the spine; its inner AUTO steps re-enter raw via the guard, so no double-wrapping, exactly one manifest per top-level call.
4. **No data/skill escape valve** (that is the point). If an operator genuinely needs the bare primitive, the only honored bypass is `LATHE_SPINE=off` set in the *real* environment before process start — and even that still emits a manifest recording `spine=disabled-by-operator`, so the bypass is itself on the record. A skill cannot set it because it is read after the process-entry clear.

**Stress test — `tools/test_spine_enforced.py` (executable probe, same method used on the gates), proving no invocation runs around its contract:**
- **Coverage:** enumerate every key in the dispatch table + bare `lathe "<goal>"` + empty `lathe ""`; run each in a subprocess against a temp `docs/ce`; assert a manifest appears carrying intake, thinking level, model, personas+why, per-step verdicts, gate verdict, cost/timing, and pass/refuse. Missing manifest ⇒ fail.
- **Exactly-one-manifest:** assert a workflow's inner AUTO step did *not* spawn a nested manifest (count == 1 per top-level invocation) — proves the guard suppresses re-wrapping.
- **Guard-forge attack (the linchpin probe):** `_LATHE_SPINE_RUN=forged lathe status` must **still** produce a manifest — proves the process-entry clear defeats a hostile pre-set guard.
- **Skill-subprocess attack:** a fake skill that shells `lathe review x` — assert the child produced its **own** manifest (can't escape by shelling out).
- **Order/halt:** inject a failing early step — assert later steps' actions never appear in the manifest and verdict == `BLOCKED`.
- **Manifest-on-crash:** monkeypatch a phase to raise — assert the manifest is **still** emitted, marked `incomplete`, verdict `ERROR`.
- **Single-raw-path invariant:** static check that `_dispatch` is underscore-private and that no `WORKFLOWS`/`CONTRACT_FOR` string reaches `_dispatch` except through `main` (grep-gate in `qa/run_gates.py`).

**Files touched:** `lathe.py` (split `main`, add guard + process-entry clear, factor `_run_workflow` out of `cmd_flow`); new pinned `tools/spine.py` (`run_spine`, `Manifest`, `apply_depth`, `resolve_thinking`); `tools/workflows.py` (add `CONTRACT_FOR` + depth table + extend `WORKFLOWS` to the full invocation set); `tools/test_spine_enforced.py` + a grep-gate in `qa/run_gates.py`. The manifest reuses `run_logger`'s existing `run_id` scheme and sits beside the structured per-run log that `lathe logs <run_id>` already reads.

**Referenced anchors:** `lathe.py:1687` (`main`/dispatch table), `:1693–1707` (body → `_dispatch`), `:943` (existing in-process `main()` re-entry to reuse), `:1688` (the FORCE-not-setdefault precedent for the guard clear), `:1679` (`LATHE_ASSUMPTION_POLICY` already wired), `cmd_flow` `:927–951` (step-loop → `_run_workflow`), `flow_report.classify_step`/`workflow_verdict` (rc→verdict, already pinned).