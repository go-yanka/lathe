"""A4 — the kanban board: a durable task store (harness.db) with a dependency DAG.

Hand-authored I/O glue (like checkpoint.py / safe_write.py) over sqlite. The DAG reasoning
(which tasks are ready, is the graph acyclic) is NOT hand-rolled here — it calls the
engine-built `tools/dag.py` (plan A4b, filled by the 26B, gated). A task = a unit of harness
work, typically "build plan NN to gated-green". The dispatcher (A5) reads `ready()` and drives
each ready task through the driver (A3).

A task row: id, title, plan_path, status, deps(json list), reason, created, updated.
status in {'pending','in_progress','done','blocked','escalated'}.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dag import ready_tasks, has_cycle   # engine-built (A4b)

DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "harness.db")
STATUSES = ("pending", "in_progress", "done", "blocked", "escalated")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conn(db_path):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def init_board(db_path=DEFAULT_DB):
    """Create the tasks table if absent. Idempotent. Returns db_path."""
    with _conn(db_path) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY, title TEXT NOT NULL, plan_path TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending', deps TEXT NOT NULL DEFAULT '[]',
            reason TEXT DEFAULT '', created TEXT NOT NULL, updated TEXT NOT NULL)""")
    return db_path


def add_task(task_id, title, plan_path="", deps=None, status="pending", db_path=DEFAULT_DB):
    """Insert (or replace) a task. deps = list of task ids it depends on. Returns the task id."""
    if status not in STATUSES:
        raise ValueError(f"bad status {status!r}; must be one of {STATUSES}")
    init_board(db_path)
    now = _now()
    with _conn(db_path) as c:
        c.execute("""INSERT INTO tasks(id,title,plan_path,status,deps,reason,created,updated)
                     VALUES(?,?,?,?,?,?,?,?)
                     ON CONFLICT(id) DO UPDATE SET title=excluded.title, plan_path=excluded.plan_path,
                       status=excluded.status, deps=excluded.deps, updated=excluded.updated""",
                  (task_id, title, plan_path, status, json.dumps(deps or []), "", now, now))
    return task_id


def _row_to_dict(r):
    d = dict(r)
    d["deps"] = json.loads(d.get("deps") or "[]")
    return d


def get_task(task_id, db_path=DEFAULT_DB):
    init_board(db_path)
    with _conn(db_path) as c:
        r = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return _row_to_dict(r) if r else None


def list_tasks(db_path=DEFAULT_DB):
    """All tasks as dicts (deps parsed to lists), in insertion order."""
    init_board(db_path)
    with _conn(db_path) as c:
        rows = c.execute("SELECT * FROM tasks ORDER BY created, id").fetchall()
    return [_row_to_dict(r) for r in rows]


def set_status(task_id, status, reason="", db_path=DEFAULT_DB):
    """Update a task's status (+optional reason, e.g. an escalation message). Returns the updated task."""
    if status not in STATUSES:
        raise ValueError(f"bad status {status!r}; must be one of {STATUSES}")
    init_board(db_path)
    with _conn(db_path) as c:
        cur = c.execute("UPDATE tasks SET status=?, reason=?, updated=? WHERE id=?",
                        (status, reason, _now(), task_id))
        if cur.rowcount == 0:
            raise KeyError(f"no task {task_id!r}")
    return get_task(task_id, db_path)


def ready(db_path=DEFAULT_DB):
    """Task ids that are pending AND have all deps done — via the engine-built DAG logic."""
    return ready_tasks(list_tasks(db_path))


def validate(db_path=DEFAULT_DB):
    """(ok, reason): False if the dependency graph has a cycle (would deadlock the dispatcher)."""
    tasks = list_tasks(db_path)
    if has_cycle(tasks):
        return False, "dependency cycle detected"
    return True, "acyclic"
