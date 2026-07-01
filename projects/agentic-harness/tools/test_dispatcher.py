"""A5 dispatcher tests — deterministic (stub drive_fn; NO engine/26B/Claude calls).
Proves the board <-> driver orchestration: ready -> drive -> write-back -> unblock dependents.
Run: python tools/test_dispatcher.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from board import add_task, get_task, init_board
from dispatcher import dispatch_once, run_board


def main():
    db = os.path.join(tempfile.mkdtemp(), "disp_test.db")
    init_board(db)

    # A scripted "driver": outcome decided by the plan_path, so the test is deterministic.
    calls = []

    def stub_drive(goal, build_attempt, repo=".", max_turns=3, on_event=None, dod=None):
        calls.append(goal)
        if "FAILPLAN" in goal:
            return {"outcome": "paused", "turns": max_turns, "reason": "budget spent", "checkpoints": max_turns}
        if "ESCALATEPLAN" in goal:
            return {"outcome": "escalate", "turns": 1, "reason": "NEEDS-YOU: pick a store", "checkpoints": 1}
        # mirror real drive's DoD gate: gated-green still escalates if road-ready DoD fails
        if dod is not None:
            ok, detail = dod()
            if not ok:
                return {"outcome": "escalate", "turns": 1, "reason": f"gated-green but {detail}", "checkpoints": 1}
        return {"outcome": "done", "turns": 1, "reason": "gates green (2/2)", "checkpoints": 1}

    # Chain: A (ok) -> B depends on A (ok). C is independent and FAILS.
    add_task("A", "build A", plan_path="plans/A.py", db_path=db)
    add_task("B", "build B", plan_path="plans/B.py", deps=["A"], db_path=db)
    add_task("C", "build C", plan_path="plans/FAILPLAN.py", db_path=db)

    # Round 1: A and C are ready (B waits on A). A->done, C->blocked.
    r1 = dispatch_once(repo=".", db_path=db, drive_fn=stub_drive)
    outs = {x["id"]: x["outcome"] for x in r1["results"]}
    assert outs == {"A": "done", "C": "paused"}, outs
    assert get_task("A", db_path=db)["status"] == "done"
    assert get_task("C", db_path=db)["status"] == "blocked"
    assert get_task("B", db_path=db)["status"] == "pending"   # still waiting (A only just finished)

    # Round 2: now B is ready (A done) -> done.
    r2 = dispatch_once(repo=".", db_path=db, drive_fn=stub_drive)
    assert {x["id"]: x["outcome"] for x in r2["results"]} == {"B": "done"}, r2
    assert get_task("B", db_path=db)["status"] == "done"

    # No more ready work.
    assert dispatch_once(repo=".", db_path=db, drive_fn=stub_drive)["results"] == []

    # run_board drives a fresh chain to completion in one call; escalate is recorded, not retried.
    db2 = os.path.join(tempfile.mkdtemp(), "disp_test2.db")
    init_board(db2)
    add_task("P", "build P", plan_path="plans/ESCALATEPLAN.py", db_path=db2)
    add_task("Q", "build Q", plan_path="plans/Q.py", db_path=db2)        # independent, ok
    summary = run_board(repo=".", db_path=db2, drive_fn=stub_drive, max_rounds=10)
    assert summary["tally"].get("done") == 1, summary          # Q done
    assert summary["tally"].get("escalated") == 1, summary     # P escalated
    assert get_task("P", db_path=db2)["reason"].startswith("NEEDS-YOU"), get_task("P", db_path=db2)

    # Cycle is refused, not run.
    db3 = os.path.join(tempfile.mkdtemp(), "disp_test3.db")
    init_board(db3)
    add_task("X", "x", plan_path="plans/X.py", deps=["Y"], db_path=db3)
    add_task("Y", "y", plan_path="plans/Y.py", deps=["X"], db_path=db3)
    assert "error" in dispatch_once(repo=".", db_path=db3, drive_fn=stub_drive), "cycle must be refused"

    # DoD wiring: a task whose plan declares a ROAD_READY that won't import -> escalated, not done.
    pdir = tempfile.mkdtemp()
    with open(os.path.join(pdir, "ship.py"), "w") as f:
        f.write("FUNCTIONS=[]\nROAD_READY={'import':'nonexistent_module_xyz'}\n")
    db4 = os.path.join(tempfile.mkdtemp(), "disp_dod.db")
    init_board(db4)
    add_task("S", "build S", plan_path="ship.py", db_path=db4)
    r = dispatch_once(repo=pdir, db_path=db4, drive_fn=stub_drive)
    assert r["results"][0]["outcome"] == "escalate", r
    assert get_task("S", db_path=db4)["status"] == "escalated"
    assert "road-ready" in get_task("S", db_path=db4)["reason"], get_task("S", db_path=db4)

    print("A5 dispatcher: ALL ASSERTIONS PASS — ready->drive->write-back, dependents unblock, "
          "escalate/blocked recorded, cycle refused, A7 DoD wired (won't-boot -> escalated). "
          "Zero engine/Claude calls (stub driver).")


if __name__ == "__main__":
    main()
