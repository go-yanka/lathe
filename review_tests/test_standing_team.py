"""ACCEPTANCE — issue #50: a standing crew of PERMANENT senior personas (Application Architect, Senior
Developer, Senior Tester), each shipping a real SOUL (ce_personas/<role>.md) authored to the CE bar, with the
Advocate's lifecycle (charter + evolving memory + severity-routed verdict). Tests the soul files' depth, the
standing_team lifecycle mechanism (pure + mock-analyst), and the wiring of the standing Architect into the
architecture step. Model-free.

  Run:  python review_tests/test_standing_team.py     (repo root)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INNER = os.path.join(ROOT, "projects", "agentic-harness")
sys.path.insert(0, os.path.join(INNER, "tools"))
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


import standing_team as ST  # noqa: E402

# 1) each standing role ships a SOUL with the five required sections (a hollow label would be a fail)
_REQUIRED = ["## What you own", "hunting for", "Severity calibration", "Standing-role lifecycle"]
for r in ST.ROLES:
    p = os.path.join(INNER, "ce_personas", r["soul"])
    body = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    check("soul present + substantial: %s" % r["soul"], len(body) > 1500, "%d chars" % len(body))
    missing = [s for s in _REQUIRED if s not in body]
    check("soul has the required sections: %s" % r["key"], not missing, "missing %s" % missing)
    check("soul defines the standing lifecycle (charter/memory/authority): %s" % r["key"],
          all(w in body.lower() for w in ("charter", "memory", "authority")), "")
    check("soul uses P0-P3 severity (routes to the review gate): %s" % r["key"], "P0" in body and "P3" in body, "")

# 2) roster + stage routing
ros = ST.roster()
check("roster lists all three standing roles", len(ros) == 3, str([r["key"] for r in ros]))
check("every standing role's soul is present", all(r["soul_present"] for r in ros), str(ros))
check("Architect presides over the 'architecture' stage", "application-architect" in [r["key"] for r in ST.for_stage("architecture")])
check("Senior Tester presides over the 'spec' stage", "senior-tester" in [r["key"] for r in ST.for_stage("spec")])

# 3) charter seed
ch = ST.seed("build an evaluator", "deliverable=CLI")
check("seed() charters the goal + framing", ch["goal"] == "build an evaluator" and "CLI" in ch["framing"], str(ch))

# 4) verdict parse + severity routing
v = ST.parse_verdict("VERDICT: block\nSEVERITY: P0\nNOTE: evaluate() is in no module — scope collapse")
check("parse_verdict reads verdict/severity/note", v["verdict"] == "block" and v["severity"] == "P0" and "scope" in v["note"], str(v))
check("blocks() true for block + P0", ST.blocks(v))
check("blocks() false for a concern/P2", not ST.blocks({"verdict": "concern", "severity": "P2"}))
vg = ST.parse_verdict("(garbled reply with no fields)")
check("parse_verdict defaults conservatively (never a silent approve)", vg["verdict"] != "approve", str(vg))

# 5) engage — pure + injectable; a mock analyst drives it, and memory accrues across engagements
def _mock(prompt):
    assert "PROJECT CHARTER" in prompt and "STANDING" in prompt.upper()   # the soul+charter+stage are in the prompt
    return "VERDICT: concern\nSEVERITY: P2\nNOTE: the 'utils' module is a grab-bag"

v1, mem1 = ST.engage("application-architect", "architecture", "<decomposition md>", ch, "", analyst_fn=_mock)
check("engage returns a parsed verdict from the persona", v1["severity"] == "P2" and "grab-bag" in v1["note"], str(v1))
check("engage accrues memory across the run", "application-architect @ architecture" in mem1, mem1)
v2, _ = ST.engage("application-architect", "architecture", "<x>", ch, analyst_fn=None)
check("engage without an analyst is a safe skip (never raises, never silent-approves)", v2["verdict"] != "approve", str(v2))

# 6) STATIC: the standing Architect is wired into the architecture step (#49)
src = open(os.path.join(ROOT, "lathe.py"), encoding="utf-8").read()
check("cmd_architect engages the standing application-architect", 'engage("application-architect"' in src)

print("\nstanding-team (#50) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
