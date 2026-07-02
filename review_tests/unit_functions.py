"""Direct unit tests for every PURE function in the Lathe toolchain — independent of the CLI.

Covers the v2.1.0 harness-built fix modules (spine_helpers, flow_report, checkin_logic, lathe_config),
the aggregators (metrics_summary), and the generated ledger demo modules (cross-module composition).

Run:  python review_tests/unit_functions.py   (exit 0 = all pass)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")
LEDGER = os.path.join(ROOT, "examples", "ledger")
sys.path.insert(0, TOOLS)
sys.path.insert(0, LEDGER)

RESULTS = []


def case(name, fn):
    try:
        fn()
        RESULTS.append((name, True, ""))
        print("  [PASS] %s" % name)
    except Exception as e:
        RESULTS.append((name, False, "%s: %s" % (type(e).__name__, e)))
        print("  [FAIL] %s -- %s: %s" % (name, type(e).__name__, e))


def t_spine_helpers():
    from spine_helpers import (resolve_out_dir, treat_missing_as_uninitialized,
                               should_auto_commit, integration_label, model_label,
                               summarize_failure)
    assert resolve_out_dir("", "/a/b/plan.py") == os.path.dirname(os.path.abspath("/a/b/plan.py"))
    assert resolve_out_dir("explicit", "/a/b/plan.py") == "explicit"
    assert treat_missing_as_uninitialized("harness.db") is True
    assert treat_missing_as_uninitialized("x.sqlite3") is True
    assert treat_missing_as_uninitialized("tools/registry.py") is False
    assert treat_missing_as_uninitialized(None) is False
    assert should_auto_commit("1") is True and should_auto_commit("yes") is True
    assert should_auto_commit("0") is False and should_auto_commit(None) is False
    assert should_auto_commit("") is False
    assert integration_label(False, True) == "n/a (no INTEGRATION defined)"
    assert integration_label(True, False) == "SKIPPED (not all functions solved)"
    assert integration_label(True, True) == "ran"
    assert model_label("gemma2:12b") == "gemma2"
    assert model_label("") == "local" and model_label(None) == "local"
    assert "error" in summarize_failure("ok line\nSome Error: boom\nlast").lower()
    assert summarize_failure(None) == "build failed"
    assert "activity log skipped" not in summarize_failure("activity log skipped: x\nreal fail")


def t_flow_report():
    from flow_report import classify_step, workflow_verdict, render_report
    assert classify_step("you", 0, "") == "todo"
    assert classify_step("auto", 1, "") == "blocked"
    assert classify_step("auto", 0, "clean output") == "pass"
    assert classify_step("auto", 0, "Traceback (most recent call last)") == "blocked"
    assert classify_step("gate", 0, "FAIL :: registry") == "blocked"
    assert workflow_verdict([]) == "PASS"
    assert workflow_verdict(["pass", "todo"]) == "PASS"
    assert workflow_verdict(["pass", "blocked", "pass"]) == "BLOCKED"
    r = render_report("wf", [("step a", "pass"), ("step b", "blocked")])
    assert "verdict: BLOCKED" in r and "[PASS] step a" in r
    try:
        render_report("wf", [("s", "bogus-status")])
        raise AssertionError("invalid status silently accepted")
    except ValueError:
        pass


def t_checkin_logic():
    from checkin_logic import is_relic, checkin_blockers
    assert is_relic("tools/__pycache__/x.pyc") is True
    assert is_relic("a/b/run.log") is True
    assert is_relic("RUN_REPORT.md") is True
    assert is_relic("tools/_fn_fails/f.txt") is True
    assert is_relic("tools/board.py") is False
    assert is_relic(None) is False
    assert checkin_blockers(True, 0, []) == []
    b = checkin_blockers(False, 2, ["x.log"])
    assert any("gates" in s for s in b) and any("ahead by 2" in s for s in b) and any("relics: 1" in s for s in b)
    assert checkin_blockers(True, True, []) == []          # bool is not "behind by N"


def t_lathe_config():
    from lathe_config import parse_config, pick
    assert parse_config('{"a": 1}') == {"a": 1}
    assert parse_config("not json") == {}
    assert parse_config(None) == {} and parse_config("") == {}
    assert parse_config("[1,2]") == {}                     # non-dict JSON rejected
    assert pick("env", "cfg", "def") == "env"
    assert pick("", "cfg", "def") == "cfg"
    assert pick("", "", "def") == "def"


def t_metrics_summary():
    from metrics_summary import metrics_summary
    rows = [
        {"build_ok": True, "functions_passed": 2, "functions_total": 2, "first_pass": 2,
         "by_local": 2, "by_claude": 0, "claude_calls": 0, "tok_total": 100,
         "fresh_attempts": 2, "per_function": [{"tries": 1}, {"tries": 1}]},
        {"build_ok": False, "functions_passed": 0, "functions_total": 1, "first_pass": 0,
         "by_local": 0, "by_claude": 0, "claude_calls": 1, "tok_total": 50,
         "fresh_attempts": 3, "per_function": [{"tries": 3}]},
    ]
    s = metrics_summary(rows)
    assert s["runs"] == 2 and s["builds_ok"] == 1
    assert 0 < s["build_success_rate"] < 1


def t_ledger_core():
    from ledger_core import parse_amount, parse_entry
    assert parse_amount("$1,234.50") == 1234.5
    assert parse_amount(" -3.00 ") == -3.0
    assert parse_amount(None) == 0.0 and parse_amount("nonsense") == 0.0
    e = parse_entry("2024-01-05, groceries, $45.20")
    assert e == {"date": "2024-01-05", "category": "groceries", "amount": 45.2}
    assert parse_entry("x,y") is None and parse_entry(None) is None


def t_ledger_stats():
    from ledger_stats import total, by_category, top_category
    es = [{"date": "d", "category": "a", "amount": 10.0},
          {"date": "d", "category": "b", "amount": 5.0},
          {"date": "d", "category": "a", "amount": 1.5}]
    assert total(es) == 16.5
    assert by_category(es) == {"a": 11.5, "b": 5.0}
    assert top_category(es) == "a"
    assert total([]) == 0.0 and top_category([]) is None


def t_ledger_composition():
    from ledger import summarize
    got = summarize(["2024-01-01,food,$10", "2024-01-02,food,$5", "2024-01-03,rent,$100"])
    assert got == {"total": 115.0, "by_category": {"food": 15.0, "rent": 100.0}, "top": "rent"}
    assert summarize(None) == {"total": 0.0, "by_category": {}, "top": None}
    assert summarize(["garbage"]) == {"total": 0.0, "by_category": {}, "top": None}


def t_board_and_dag():
    import tempfile
    import board
    import dag
    db = tempfile.mktemp(suffix=".db")
    board.init_board(db)
    board.add_task("t1", "goal one", db_path=db)
    board.add_task("t2", "goal two", deps=["t1"], db_path=db)
    ts = board.list_tasks(db)
    assert len(ts) == 2
    assert board.ready(db_path=db) == ["t1"]                 # t2 blocked behind t1
    board.set_status("t1", "done", "built", db_path=db)
    assert board.ready(db_path=db) == ["t2"]                 # dep done -> t2 unblocked
    assert not dag.has_cycle(board.list_tasks(db))
    r = dag.ready_tasks([{"id": "a", "status": "pending", "deps": ["b"]},
                         {"id": "b", "status": "pending", "deps": []}])
    assert r == ["b"]                                        # only dep-free tasks are ready (returns ids)
    assert dag.has_cycle([{"id": "a", "status": "pending", "deps": ["b"]},
                          {"id": "b", "status": "pending", "deps": ["a"]}])
    os.unlink(db)


def main():
    print("== unit tests: pure toolchain functions ==")
    for name, fn in [
        ("spine_helpers (B1/B2/B4/B5/B6/B7 logic)", t_spine_helpers),
        ("flow_report (workflow verdicts)", t_flow_report),
        ("checkin_logic (relics/blockers)", t_checkin_logic),
        ("lathe_config (parse/precedence)", t_lathe_config),
        ("metrics_summary (aggregator)", t_metrics_summary),
        ("ledger_core (generated, plan 1)", t_ledger_core),
        ("ledger_stats (generated, plan 2)", t_ledger_stats),
        ("ledger composition (plan 3 imports 1+2)", t_ledger_composition),
        ("board + dag (sqlite kanban, topo)", t_board_and_dag),
    ]:
        case(name, fn)
    bad = [r for r in RESULTS if not r[1]]
    print("\nunit_functions: %d/%d groups pass" % (len(RESULTS) - len(bad), len(RESULTS)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
