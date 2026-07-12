"""ACCEPTANCE — #37: the persona bandit's EXPLOIT signal actually forms now.

The UCB1 decider grades personas on VERIFIED findings, but the only ledger writer (record_run, at SELECTION
time) always passed contributions={}, so raised/confirmed were always 0 -> grades.json was never written ->
the bandit could only ever EXPLORE (grade=0 for everyone). `record_outcomes` is the missing post-review
feedback: an ENGAGED lens produced verifiable findings, so it scores; a non-engaged one does not.

Model-free (monkeypatches the ledger/grades paths to a temp dir).
Run:  python review_tests/test_bandit_grades.py     (repo root)
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
import persona_orchestrator as PO  # noqa: E402
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


tmp = tempfile.mkdtemp(prefix="bandit_")
_led = os.path.join(tmp, "usage_ledger.jsonl")
_grd = os.path.join(tmp, "grades.json")
PO.ledger_path = lambda: _led
PO.grades_path = lambda: _grd
PO.manifests_dir = lambda: os.path.join(tmp, "manifests")

# 0) precondition: no grades yet (the whole bug is that this file never appeared)
check("grades.json absent before any outcome", not os.path.exists(_grd))

# 1) an engaged lens forms a grade — the exploit signal that never used to appear
g = PO.record_outcomes({"security": True, "correctness": True, "perf": False}, "run1")
check("record_outcomes returns non-empty grades", bool(g), str(g))
check("grades.json is WRITTEN", os.path.exists(_grd))
check("an ENGAGED lens has a grade > 0", g.get("security", 0) > 0, str(g))
check("a NON-engaged lens is NOT graded (no false credit)", "perf" not in g, str(g))

# 2) the ledger recorded raised>0 (not the old always-empty 0/0)
recs = [json.loads(l) for l in open(_led, encoding="utf-8") if l.strip()]
check("ledger has a row with raised>0 (real work recorded)", any(r.get("raised", 0) > 0 for r in recs), str(recs[:2]))

# 3) dict form (richer raised/confirmed) is accepted and scores
g2 = PO.record_outcomes({"security": {"raised": 2, "confirmed": 2}}, "run2")
check("dict outcome form is accepted + graded", g2.get("security", 0) > 0, str(g2))

# 4) an all-inoperative review writes NOTHING (no phantom grades)
tmp2 = tempfile.mkdtemp(prefix="bandit2_")
PO.ledger_path = lambda: os.path.join(tmp2, "usage_ledger.jsonl")
PO.grades_path = lambda: os.path.join(tmp2, "grades.json")
g3 = PO.record_outcomes({"security": False, "correctness": False}, "run3")
check("an all-inoperative review forms NO grades",
      g3 == {} and not os.path.exists(os.path.join(tmp2, "grades.json")), str(g3))

# 5) STATIC: cmd_review actually wires record_outcomes into the grade-feedback block
src = open(os.path.join(ROOT, "lathe.py"), encoding="utf-8").read()
check("cmd_review feeds review outcomes to the bandit (record_outcomes)", ".record_outcomes(" in src)

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(tmp2, ignore_errors=True)
print("\nbandit-grades (#37) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
