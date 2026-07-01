"""Deterministic test for autonomy_live's outer loop. Mocks all real I/O (no Claude/engine/git),
uses a temp board db, and asserts the self-feeding control flow: plan -> save -> run -> done,
plus Rule-of-Three escalation on repeated failure."""
import importlib.util
import os
import tempfile

def load(n):
    s = importlib.util.spec_from_file_location(n, os.path.join(os.path.dirname(os.path.abspath(__file__)), n + ".py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

live = load("autonomy_live")
board = load("board")

# a minimal VALID plan (must satisfy plan_validator.is_valid_plan: OUT_DIR/MODULE_NAME/FUNCTIONS+tests)
CANNED = (
    'OUT_DIR = r"x"\n'
    'MODULE_NAME = "demo_fn"\n'
    'HEADER = ""\n'
    'GLUE = ""\n'
    'FUNCTIONS = [{"name":"demo_fn","prompt":"add one","tests":["assert demo_fn(1)==2"]}]\n'
)


def _mock_deps(db_path, run_result):
    """Build mock deps over a temp board. request_spec returns the canned plan once then ''."""
    state = {"seq": 0, "asked": 0, "commits": []}

    def request_spec(prompt):
        state["asked"] += 1
        return CANNED if state["asked"] == 1 else ""    # one plan, then empty -> reject -> stop

    def save_plan(text):
        state["seq"] += 1
        tid = "auto_%03d" % state["seq"]
        board.add_task(tid, tid, plan_path=tid + ".py", status="pending", db_path=db_path)
        return board.get_task(tid, db_path=db_path)

    def run_task(task):
        return run_result

    def commit(msg):
        state["commits"].append(msg)

    return {"request_spec": request_spec, "save_plan": save_plan, "run_task": run_task, "commit": commit}, state


def test_happy_path_self_feeds():
    db = os.path.join(tempfile.mkdtemp(), "t.db")
    deps, state = _mock_deps(db, {"ok": True, "reason": "1/1 gated green"})
    tr = live.run("build a demo helper", max_steps=10, build_one=True, db_path=db, deps=deps)
    steps = [r["step"] for r in tr]
    assert "planned" in steps, steps           # board empty -> requested a spec
    assert "ran_ok" in steps, steps            # then built it green
    assert state["commits"], "should have committed the green build"
    done = [t for t in board.list_tasks(db) if t["status"] == "done"]
    assert len(done) == 1, [t["status"] for t in board.list_tasks(db)]
    print("test_happy_path_self_feeds OK ->", steps)


def test_rule_of_three_escalates():
    db = os.path.join(tempfile.mkdtemp(), "t.db")
    deps, state = _mock_deps(db, {"ok": False, "reason": "gate red"})
    tr = live.run("build a doomed helper", max_steps=12, build_one=False, db_path=db, deps=deps)
    fails = [r for r in tr if r["step"] == "ran_failed"]
    assert len(fails) == 3, "Rule-of-Three: expected exactly 3 failures before escalate, got %d" % len(fails)
    esc = [t for t in board.list_tasks(db) if t["status"] == "escalated"]
    assert len(esc) == 1, [t["status"] for t in board.list_tasks(db)]
    print("test_rule_of_three_escalates OK ->", [r["step"] for r in tr])


if __name__ == "__main__":
    test_happy_path_self_feeds()
    test_rule_of_three_escalates()
    print("ALL autonomy_live tests passed")
