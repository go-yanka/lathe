"""A5 — the dispatcher: turns the board into autonomous multi-task progress.

Reads ready tasks off the board (A4), drives each to gated-green through the driver (A3,
checkpoint + goal loop + deterministic gate), and writes the outcome back as a status:
  driver 'done'     -> task 'done'
  driver 'escalate' -> task 'escalated' (reason kept; this is a hand-off to the orchestrator)
  driver 'paused'   -> task 'blocked'   (budget spent; can be retried/re-specced)

`run_board` loops dispatch until nothing is ready — the overnight autonomous runner. A task
that escalates does NOT block unrelated tasks; only its dependents stay pending. No programmatic
Claude calls anywhere — the default judge is deterministic; escalations hand off in-band.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from board import ready, get_task, set_status, validate, DEFAULT_DB
from driver import drive, run_plan, make_dod

_OUTCOME_TO_STATUS = {"done": "done", "escalate": "escalated", "paused": "blocked"}


def _plan_road_ready(plan_path, repo):
    """Read a plan's optional ROAD_READY spec (the A7 DoD). Tolerant: returns {} if the plan
    file is missing or won't import — the DoD is then just the unit gates (correct for pure-lib plans)."""
    import importlib.util
    full = os.path.join(repo, plan_path)
    try:
        spec = importlib.util.spec_from_file_location("plan_dod", full)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return dict(getattr(mod, "ROAD_READY", {}) or {})
    except Exception:
        return {}


def dispatch_once(repo=".", db_path=DEFAULT_DB, drive_fn=drive, n=6, max_turns=3, timeout=600, on_event=None):
    """Drive every currently-ready task once. Returns {'results': [...]} or {'error': ...} on a cycle."""
    ok, why = validate(db_path)
    if not ok:
        return {"error": why}

    results = []
    for tid in ready(db_path):
        task = get_task(tid, db_path)
        set_status(tid, "in_progress", db_path=db_path)
        plan = task.get("plan_path") or ""
        if not plan:
            set_status(tid, "escalated", reason="no plan_path on task", db_path=db_path)
            results.append({"id": tid, "outcome": "escalate", "reason": "no plan_path"})
            continue
        goal = f"build {plan} to gated-green"
        dod = make_dod(_plan_road_ready(plan, repo), repo)   # A7 DoD if the plan declares ROAD_READY
        r = drive_fn(goal, lambda t, last: run_plan(plan, repo, n=n, timeout=timeout),
                     repo=repo, max_turns=max_turns, on_event=on_event, dod=dod)
        status = _OUTCOME_TO_STATUS.get(r.get("outcome"), "blocked")
        set_status(tid, status, reason=str(r.get("reason", ""))[:300], db_path=db_path)
        results.append({"id": tid, "outcome": r.get("outcome"), "reason": r.get("reason")})
    return {"results": results}


def run_board(repo=".", db_path=DEFAULT_DB, drive_fn=drive, max_rounds=50, on_event=None, **kw):
    """Loop dispatch_once until no task is ready (all done/blocked/escalated, or deps unsatisfiable).
    Returns a summary: rounds run, per-round results, and the final status tally."""
    rounds = []
    for _ in range(max_rounds):
        if not ready(db_path):
            break
        out = dispatch_once(repo=repo, db_path=db_path, drive_fn=drive_fn, on_event=on_event, **kw)
        rounds.append(out)
        if "error" in out or not out.get("results"):
            break
    from board import list_tasks
    tally = {}
    for t in list_tasks(db_path):
        tally[t["status"]] = tally.get(t["status"], 0) + 1
    return {"rounds": len(rounds), "detail": rounds, "tally": tally}
