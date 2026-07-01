"""A6 — decompose: turn a directory of plans into a runnable board (the mechanical half).

The FUZZY half of decomposition (a vague goal -> a set of specs/plans) is JUDGMENT, so per the
binding cost principle it stays with the orchestrator session (me, in-band) — never a programmatic
Claude call. A6 is the DETERMINISTIC half: once the plans exist, scan them and seed one board task
per plan, wiring dependencies from each plan's optional `DEPENDS_ON = [<plan-stem>, ...]`. After
that the dispatcher (A5) can drive the whole board to gated-green on its own.

A plan stem (filename without .py) is the task id. Plans prefixed with '_' (e.g. _design.py)
are treated as shared library, not tasks, and skipped.
"""
import glob
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from board import add_task, validate, DEFAULT_DB


def _load_plan(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed_from_plans(plans_dir, db_path=DEFAULT_DB, repo=None):
    """Create one board task per plan file in plans_dir. Deps come from each plan's DEPENDS_ON.
    Returns {'seeded': [ids], 'ok': bool, 'reason': str} where ok=False means a dependency cycle.
    Idempotent (add_task upserts), so re-running re-syncs the board to the plans on disk."""
    seeded = []
    for path in sorted(glob.glob(os.path.join(plans_dir, "*.py"))):
        stem = os.path.basename(path)[:-3]
        if stem.startswith("_"):
            continue
        try:
            mod = _load_plan(path)
        except Exception as e:
            # A plan that won't even import becomes an escalated task, not a silent skip.
            rel = os.path.relpath(path, repo) if repo else path
            add_task(stem, f"build {stem} (PLAN IMPORT ERROR)", plan_path=rel,
                     status="escalated", db_path=db_path)
            seeded.append(stem)
            continue
        deps = list(getattr(mod, "DEPENDS_ON", []) or [])
        title = getattr(mod, "TITLE", None) or f"build {stem}"
        rel = os.path.relpath(path, repo) if repo else path
        add_task(stem, title, plan_path=rel, deps=deps, db_path=db_path)
        seeded.append(stem)

    ok, reason = validate(db_path)
    return {"seeded": seeded, "ok": ok, "reason": reason}
