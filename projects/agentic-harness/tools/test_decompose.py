"""A6 decompose tests — seed a board from plan files (deterministic; temp dirs only).
Run: python tools/test_decompose.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from board import init_board, list_tasks, get_task, ready
from decompose import seed_from_plans


def _write(d, name, body):
    with open(os.path.join(d, name), "w") as f:
        f.write(body)


def main():
    plans = tempfile.mkdtemp()
    _write(plans, "p1.py", "TITLE='build p1'\nMODULE_NAME='p1'\nFUNCTIONS=[]\n")
    _write(plans, "p2.py", "TITLE='build p2'\nDEPENDS_ON=['p1']\nMODULE_NAME='p2'\nFUNCTIONS=[]\n")
    _write(plans, "_design.py", "TOKENS={}\n")           # shared lib — must be skipped
    _write(plans, "p3broken.py", "def x(:\n")            # import error — becomes escalated task

    db = os.path.join(tempfile.mkdtemp(), "seed.db")
    init_board(db)
    r = seed_from_plans(plans, db_path=db)

    # 1. tasks for p1, p2, p3broken — NOT _design
    assert set(r["seeded"]) == {"p1", "p2", "p3broken"}, r
    assert r["ok"] is True, r

    # 2. dep wired from DEPENDS_ON; title read from plan
    t2 = get_task("p2", db_path=db)
    assert t2["deps"] == ["p1"] and t2["title"] == "build p2", t2

    # 3. only p1 is ready (p2 waits on p1; broken one is escalated, not pending)
    assert ready(db_path=db) == ["p1"], ready(db_path=db)

    # 4. the un-importable plan is recorded as escalated (surfaced, not silently dropped)
    assert get_task("p3broken", db_path=db)["status"] == "escalated", get_task("p3broken", db_path=db)

    # 5. idempotent re-seed: same task set, no duplicates
    r2 = seed_from_plans(plans, db_path=db)
    assert set(r2["seeded"]) == {"p1", "p2", "p3broken"}
    assert len(list_tasks(db_path=db)) == 3, list_tasks(db_path=db)

    # 6. cycle in DEPENDS_ON is reported (ok=False)
    cyc = tempfile.mkdtemp()
    _write(cyc, "a.py", "DEPENDS_ON=['b']\nFUNCTIONS=[]\n")
    _write(cyc, "b.py", "DEPENDS_ON=['a']\nFUNCTIONS=[]\n")
    db2 = os.path.join(tempfile.mkdtemp(), "seed2.db")
    init_board(db2)
    rc = seed_from_plans(cyc, db_path=db2)
    assert rc["ok"] is False and "cycle" in rc["reason"], rc

    print("A6 decompose: ALL 6 ASSERTIONS PASS — plans->board, deps from DEPENDS_ON, "
          "_libs skipped, broken plan escalated, idempotent, cycle reported.")


if __name__ == "__main__":
    main()
