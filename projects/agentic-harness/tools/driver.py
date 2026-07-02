"""A3 — the autonomous driver. Composes the safety + autonomy layers into one thing:

    checkpoint (A0)  →  goal loop (A2, Claude judge)  →  done / escalate / paused

`drive()` snapshots the working tree BEFORE every build attempt (so any bad build is
rollback-recoverable), then runs the goal loop until the judge says the goal is met,
the loop escalates (needs a human), or the turn budget is spent.

`run_plan()` is the real build attempt for the harness: it runs a plan through `hrun.py`
(Claude-authored spec → 26B fills → gates verify) and returns the gate output; the Claude
judge reads that output to decide done-ness — we never hand-parse pass/fail.

This is the keystone: with A3, the harness pursues a goal to gated-green on its own, on top
of the corruption insurance (A0/A1). The 26B only ever fills tiny gated regions — never free-hands.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from checkpoint import snapshot
from goal_loop import run_goal_loop, gate_judge   # default judge = deterministic gates (no Claude calls)


def run_plan(plan_path: str, repo: str, model: str = "openai:g26b", n: int = 8, timeout: int = 900) -> str:
    """Real build attempt: run one plan through hrun.py; return the gate output (raw).
    The judge interprets pass/fail — we don't hand-parse it here."""
    try:
        r = subprocess.run([sys.executable, "hrun.py", plan_path, model, str(n)],
                           cwd=repo, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        if "Traceback (most recent call last)" in out:            # B7: a crash -> one-line summary, never a raw traceback dump
            try:
                from spine_helpers import summarize_failure
                return "[build error] " + summarize_failure(out)
            except Exception:
                pass
        return out[-1500:] if out else f"[hrun produced no output, rc={r.returncode}]"
    except subprocess.TimeoutExpired:
        return f"[hrun TIMEOUT after {timeout}s on {plan_path}]"
    except Exception as e:
        return f"[hrun error: {e}]"


def make_dod(spec: dict, repo: str):
    """Build a Definition-of-Done callable from a plan's ROAD_READY spec (A7 stages).

    spec keys (all optional): 'import' (module name), 'boot' (server cmd list) + 'health' (url),
    'e2e' (cmd list), 'cwd' (path relative to repo), 'timeout'. Returns () -> (ok, detail), or
    None if the spec is empty (no DoD = unit gates are the whole bar, fine for pure-lib plans)."""
    if not spec:
        return None
    from road_ready import road_ready, import_stage, boot_health_stage, command_stage
    cwd = os.path.join(repo, spec["cwd"]) if spec.get("cwd") else repo
    stages = []
    if spec.get("import"):
        stages.append(("import", import_stage(spec["import"], cwd=cwd)))
    if spec.get("boot") and spec.get("health"):
        stages.append(("boot+health", boot_health_stage(spec["boot"], spec["health"],
                                                         cwd=cwd, timeout=spec.get("timeout", 25))))
    if spec.get("e2e"):
        stages.append(("e2e", command_stage("e2e", spec["e2e"], cwd=cwd, timeout=spec.get("timeout", 300))))

    def dod():
        r = road_ready(stages)
        names = ", ".join(s["name"] for s in r["results"])
        if r["ok"]:
            return True, f"road-ready ({names})"
        bad = next((s["detail"] for s in r["results"] if s["name"] == r["failed"]), "")
        return False, f"NOT road-ready — failed at {r['failed']}: {bad}"
    return dod


def drive(goal: str, build_attempt, repo: str = ".", judge=gate_judge,
          max_turns: int = 10, on_event=None, dod=None) -> dict:
    """Autonomously drive `build_attempt` to satisfy `goal`, with a checkpoint before each attempt.

    build_attempt(turn, last_result) -> result_str   (e.g. lambda t, _: run_plan("plans/A0.py", repo))
    dod: optional () -> (ok, detail) Definition-of-Done (A7 road-ready). Runs ONCE after the loop
         says 'done'; if it fails, the build was gated-green but doesn't actually boot/ship, so the
         outcome is downgraded to 'escalate' (hand off, don't mark done). This is the 'green != shippable' guard.
    Returns the goal-loop outcome dict {outcome, turns, reason}, plus 'checkpoints' taken.
    """
    taken = []

    def step(turn, last_result):
        sha = snapshot(repo, f"goal '{goal[:40]}' turn {turn}")   # A0 safety net before each build
        if sha:
            taken.append(sha)
        return build_attempt(turn, last_result)

    result = run_goal_loop(goal, step, judge=judge, max_turns=max_turns, on_event=on_event)
    result["checkpoints"] = len(taken)

    # Final DoD gate: unit-gated green is necessary but not sufficient — it must also boot.
    if result.get("outcome") == "done" and dod is not None:
        try:
            ok, detail = dod()
        except Exception as e:
            ok, detail = False, f"DoD raised: {e}"
        if ok:
            result["reason"] = f"{result.get('reason', '')} + {detail}"
        else:
            result = {"outcome": "escalate", "turns": result["turns"],
                      "reason": f"gated-green but {detail}", "checkpoints": len(taken)}
    return result
