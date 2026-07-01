"""A4 board tests — executable spec for the durable task store + DAG readiness.
Uses a temp DB (never touches the real harness.db). Run: python tools/test_board.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from board import (add_task, get_task, list_tasks, set_status, ready, validate, init_board)


def main():
    db = os.path.join(tempfile.mkdtemp(), "harness_test.db")
    init_board(db)

    # 1. add + read back, deps round-trip as a list
    add_task("A", "build plan A0", plan_path="plans/A0.py", db_path=db)
    add_task("B", "build plan A1", plan_path="plans/A1.py", deps=["A"], db_path=db)
    t = get_task("B", db_path=db)
    assert t["title"] == "build plan A1" and t["deps"] == ["A"] and t["status"] == "pending", t

    # 2. readiness via the engine-built DAG: only A is ready (B waits on A)
    assert ready(db_path=db) == ["A"], ready(db_path=db)

    # 3. finish A -> B becomes ready, A drops out
    set_status("A", "done", db_path=db)
    assert ready(db_path=db) == ["B"], ready(db_path=db)

    # 4. in_progress is not ready
    set_status("B", "in_progress", db_path=db)
    assert ready(db_path=db) == [], ready(db_path=db)

    # 5. escalation carries a reason
    set_status("B", "escalated", reason="needs a human: pick session store", db_path=db)
    assert get_task("B", db_path=db)["reason"].startswith("needs a human"), get_task("B", db_path=db)

    # 6. validate catches a cycle
    add_task("X", "x", deps=["Y"], db_path=db)
    add_task("Y", "y", deps=["X"], db_path=db)
    ok, why = validate(db_path=db)
    assert ok is False and "cycle" in why, (ok, why)

    # 7. bad status is rejected
    try:
        set_status("A", "frobnicated", db_path=db)
        assert False, "should have raised on bad status"
    except ValueError:
        pass

    # 8. list_tasks returns all, deps parsed
    ids = {t["id"] for t in list_tasks(db_path=db)}
    assert ids == {"A", "B", "X", "Y"}, ids

    print("A4 board: ALL 8 ASSERTIONS PASS — durable store + DAG readiness (engine-built dag.py) + cycle guard.")


if __name__ == "__main__":
    main()
