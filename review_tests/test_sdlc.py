"""ACCEPTANCE TEST — #41: SDLC authoring with the RTM gate (requirements are traceable or refused).

  1. rtm_gaps (harness-built): full-chain set passes; orphans/dangling refs/duplicates each refused.
  2. `lathe sdlc` e2e with a MOCKED analyst: a broken first answer triggers the gap feedback retry; a
     fixed second answer passes -> REQUIREMENTS.md + rtm.json written with the traced tables + CRITERIA block.
  3. an analyst that never fixes its gaps -> REFUSED (rc!=0), nothing written.
Offline (analyst mocked; the live path was proven separately: Fable authored 21 traced items, gate PASS).
Run:  python review_tests/test_sdlc.py     (repo root)
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
from sdlc_rtm import rtm_gaps

fails = []
def check(name, ok, detail=""):
    print("  %-62s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

GOOD = {"UC": [{"id": "UC-1", "text": "watch a folder"}],
        "BR": [{"id": "BR-1", "text": "no file lost", "traces_to": ["UC-1"]}],
        "FR": [{"id": "FR-1", "text": "detect new files", "traces_to": ["BR-1"]}],
        "TS": [{"id": "TS-1", "text": "poll mtime every 2s", "traces_to": ["FR-1"]}]}
BAD = {"UC": [{"id": "UC-1", "text": "watch a folder"}],
       "BR": [{"id": "BR-1", "text": "no file lost", "traces_to": ["UC-9"]}], "FR": [], "TS": []}

check("full chain passes the RTM gate", rtm_gaps(GOOD) == [])
check("dangling ref refused", any("unknown" in g for g in rtm_gaps(BAD)))
check("uncovered UC refused", any("covers" in g for g in rtm_gaps({"UC": GOOD["UC"], "BR": [], "FR": [], "TS": []})))

def run_sdlc(answers, out):
    """Drive cmd_sdlc with a scripted analyst."""
    fake = types.ModuleType("request_spec")
    seq = list(answers)
    fake.request_spec = lambda prompt: seq.pop(0) if seq else ""
    sys.modules["request_spec"] = fake
    spec = importlib.util.spec_from_file_location("lathe_mod", os.path.join(ROOT, "lathe.py"))
    lathe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lathe)
    rc = lathe.cmd_sdlc(["goal for the test", "--out", out])
    del sys.modules["request_spec"]
    return rc

tmp = tempfile.mkdtemp(prefix="sdlc_")
# 2) broken first answer -> gap feedback -> fixed second answer -> artifacts written
rc = run_sdlc([json.dumps(BAD), json.dumps(GOOD)], tmp)
check("gap-then-fix: exits 0 after the feedback retry", rc == 0, "rc=%r" % rc)
req = os.path.join(tmp, "REQUIREMENTS.md")
check("REQUIREMENTS.md written with traced tables",
      os.path.exists(req) and "UC-1" in open(req, encoding="utf-8").read() and "TS-1" in open(req, encoding="utf-8").read())
check("CRITERIA block suggested (TS -> criteria)", "CRITERIA = [" in open(req, encoding="utf-8").read())
check("rtm.json written", os.path.exists(os.path.join(tmp, "rtm.json")))

# 3) never-fixing analyst -> refused, nothing written
tmp2 = tempfile.mkdtemp(prefix="sdlc2_")
rc = run_sdlc([json.dumps(BAD), json.dumps(BAD)], tmp2)
check("persistent gaps -> REFUSED (rc!=0)", rc != 0, "rc=%r" % rc)
check("nothing written on refusal", not os.path.exists(os.path.join(tmp2, "REQUIREMENTS.md")))

shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(tmp2, ignore_errors=True)
print("\nsdlc acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
