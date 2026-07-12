"""ACCEPTANCE — #37: the persona bandit's grade reflects VALUE FOUND, not merely that a lens "engaged".

Before: the only ledger writer (record_run, at SELECTION time) always passed contributions={}, so raised/
confirmed were 0 -> grades.json never formed -> the bandit only explored. The first naive fix credited every
ENGAGED lens 1/1 (ran-without-crashing). This test proves the REAL fix: findings are parsed for a COUNT
(raised) and how many were high-severity P0/P1 (confirmed), and record_outcomes turns that into grades — so a
lens that surfaces real issues out-grades one that emits low-severity noise.

Model-free (monkeypatches the ledger/grades paths). Run: python review_tests/test_bandit_grades.py
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")
sys.path.insert(0, TOOLS)
import review_gate as RG          # noqa: E402
import persona_orchestrator as PO  # noqa: E402
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


# ---- count_findings: parse a REAL hreview-format findings file for (raised, confirmed) ----
findings = (
    "Lens: security — 3 findings\n"
    "critical | auth.py:login | SQLi via f-string | parameterize\n"
    "high | net.py:fetch | no timeout -> hang | add timeout=30\n"
    "low | util.py:x | minor naming | rename\n"
    "That's the critical path summary; overall high quality otherwise.\n"   # prose -> must NOT count
)
r, c = RG.count_findings(findings)
check("count_findings counts real finding lines as raised (3, not the prose)", r == 3, "raised=%s" % r)
check("count_findings counts P0/P1 (critical+high) as confirmed (2)", c == 2, "confirmed=%s" % c)
check("count_findings ignores prose with no severity-pipe", RG.count_findings("all clean, no issues")[0] == 0)

# ---- record_outcomes exists and forms grades from the dict (value) form ----
check("persona_orchestrator.record_outcomes exists", hasattr(PO, "record_outcomes"))
tmp = tempfile.mkdtemp(prefix="bandit_")
PO.ledger_path = lambda: os.path.join(tmp, "usage_ledger.jsonl")
PO.grades_path = lambda: os.path.join(tmp, "grades.json")
PO.manifests_dir = lambda: os.path.join(tmp, "manifests")

# THE value-weighting assertion: two lenses with the SAME activity (raised=4) but different VALUE (confirmed)
# must NOT grade equally — the high-confirmed lens outscores the all-low-severity 'noisy' one. Under the naive
# engaged=1/1 scheme both would be identical, so this fails on the pre-fix wiring.
g = PO.record_outcomes({"good": {"raised": 4, "confirmed": 4}, "noisy": {"raised": 4, "confirmed": 0}}, "run1")
check("grades.json is written from record_outcomes", os.path.exists(PO.grades_path()))
check("a high-value lens (4/4) is graded > 0", g.get("good", 0) > 0, str(g))
check("value-weighting: high-confirmed 'good' out-grades all-low-severity 'noisy'",
      g.get("good", 0) > g.get("noisy", 0), str(g))

# a lens that surfaced NOTHING (raised=0) contributes no gradeable work
tmp2 = tempfile.mkdtemp(prefix="bandit2_")
PO.ledger_path = lambda: os.path.join(tmp2, "usage_ledger.jsonl")
PO.grades_path = lambda: os.path.join(tmp2, "grades.json")
g2 = PO.record_outcomes({"quiet": {"raised": 0, "confirmed": 0}}, "run2")
check("a lens that found nothing (raised=0) is not graded", "quiet" not in g2, str(g2))

# ---- the cmd_review wiring feeds count_findings -> record_outcomes (value form, not engaged=1) ----
src = open(os.path.join(ROOT, "lathe.py"), encoding="utf-8").read()
check("cmd_review parses findings via count_findings for the bandit", "count_findings(" in src)
check("cmd_review feeds the {raised,confirmed} dict form to record_outcomes",
      ("record_outcomes(_outcomes37" in src) and ('"raised": _raised37' in src))

for d in (tmp, tmp2):
    shutil.rmtree(d, ignore_errors=True)
print("\nbandit-grades (#37) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
