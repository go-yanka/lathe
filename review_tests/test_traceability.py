"""ACCEPTANCE TEST — enforcement mechanism #2: requirement->test traceability, enforced.
(docs/METHODOLOGY_ENFORCEMENT_VALIDATION.md build-spec item 2. A mechanism is not "done" until this passes.)

Asserts, per the spec:
  1. a plan with an UNMAPPED criterion (no 'tests') is REFUSED by the validator;
  2. a plan whose criterion maps to a DANGLING ref (unknown fn / out-of-range idx) is REFUSED;
  3. a fully-mapped plan is ACCEPTED;
  4. `lathe trace <plan>` emits the criterion->test->pin->model matrix (after a real gated build, so the
     pin column is populated) and exits 0 with every criterion covered.

Needs: a local implementer for step 4's build (default http://127.0.0.1:8089; set LOCAL_OPENAI_URL).
If the endpoint is unreachable, steps 1-3 still run and step 4 is reported as SKIPPED (rc stays 0) —
the ENFORCEMENT half is endpoint-independent; only the pin-column demo needs a model.
Run:  python review_tests/test_traceability.py     (repo root)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
import plan_validator

tmp = tempfile.mkdtemp(prefix="trace_")
fails = []
def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

BASE = """OUT_DIR = r%r
MODULE_NAME = "tr_mod"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {"name": "add2", "prompt": "Write add2(x) returning x+2. Output ONLY the function code.",
     "tests": ["assert add2(1) == 3", "assert add2(-2) == 0"]},
]
CRITERIA = %s
"""

def verdict(criteria_literal):
    return plan_validator.is_valid_plan(BASE % (tmp, criteria_literal))

# 1) UNMAPPED criterion -> REFUSED
v = verdict("[{'id': 'AC-1', 'text': 'adds two', 'tests': []}]")
check("unmapped criterion is REFUSED", not v["ok"] and "UNMAPPED" in v["reason"], v["reason"])
v = verdict("[{'id': 'AC-1', 'text': 'adds two'}]")
check("criterion missing 'tests' entirely is REFUSED", not v["ok"], v["reason"])

# 2) DANGLING refs -> REFUSED
v = verdict("[{'id': 'AC-1', 'text': 'adds two', 'tests': ['ghost_fn']}]")
check("unknown-function ref is REFUSED (dangling)", not v["ok"] and "dangling" in v["reason"], v["reason"])
v = verdict("[{'id': 'AC-1', 'text': 'adds two', 'tests': ['add2:9']}]")
check("out-of-range test index is REFUSED", not v["ok"] and "out of range" in v["reason"], v["reason"])
v = verdict("[{'id': 'AC-1', 'text': 'a', 'tests': ['add2']}, {'id': 'AC-1', 'text': 'b', 'tests': ['add2']}]")
check("duplicate criterion ids are REFUSED", not v["ok"] and "duplicate" in v["reason"], v["reason"])

# 3) fully-mapped -> ACCEPTED (and criteria-free plans stay valid: backward compatible)
v = verdict("[{'id': 'AC-1', 'text': 'adds two to any int', 'tests': ['add2']}, "
            "{'id': 'AC-2', 'text': 'handles negatives', 'tests': ['add2:1']}]")
check("fully-mapped criteria are ACCEPTED", v["ok"], v["reason"])
v = plan_validator.is_valid_plan(BASE.replace("CRITERIA = %s\n", "") % (tmp,))
check("plans without CRITERIA remain valid (opt-in)", v["ok"], v["reason"])

# 4) the matrix: real gated build -> `lathe trace` emits criterion->test->pin->model, rc 0
plan_path = os.path.join(tmp, "plan_traced.py")
open(plan_path, "w", encoding="utf-8").write(BASE % (tmp,
    "[{'id': 'AC-1', 'text': 'adds two to any int', 'tests': ['add2']}, "
    "{'id': 'AC-2', 'text': 'handles negatives', 'tests': ['add2:1']}]"))
url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
reachable = True
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    reachable = "HTTP" in str(type(e).__name__)          # any HTTP response = up; connection error = down
if reachable:
    env = dict(os.environ, LOCAL_OPENAI_URL=url)
    b = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), plan_path, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    built = '"build_ok": true' in (b.stdout or "")
    check("gated build of the traced plan is green", built, (b.stdout or "")[-300:])
    t = subprocess.run([sys.executable, os.path.join(ROOT, "lathe.py"), "trace", plan_path],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=60)
    out = t.stdout or ""
    check("trace exits 0 with all criteria covered", t.returncode == 0, "rc=%d\n%s" % (t.returncode, out[-400:]))
    check("matrix has criterion->test rows for AC-1 and AC-2", "AC-1" in out and "AC-2" in out)
    check("matrix shows the PIN hash (provenance)", bool(re.search(r"AC-1\s+add2\s+[0-9a-f]{12}", out)), out[-400:])
    check("matrix shows the model", "openai:local" in out)
else:
    print("  (step 4 SKIPPED — no implementer endpoint at %s; enforcement steps 1-3 fully verified)" % url)

shutil.rmtree(tmp, ignore_errors=True)
print("\ntraceability acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
