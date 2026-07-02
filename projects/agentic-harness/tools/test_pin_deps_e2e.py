"""Transitive pin invalidation e2e (review V3 §3) — the claim-level repro, not a unit test.

Scenario (the reviewer's exact hole): plan has A and B where B's code calls A.
  build 1: both generated + pinned.
  build 2 (nothing changed): both REUSED from pin, zero model calls.  (reproducibility intact)
  build 3 (A's SPEC changed): A regenerates AND B's pin is INVALIDATED (B not 'pinned') — before this fix
           B kept its pin because B's own key didn't change, i.e. stale-but-green.
Runs on the real local 9B (cheap); trivial functions so generation is reliable.
Run:  python projects/agentic-harness/tools/test_pin_deps_e2e.py     (repo root)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ENGINE = os.path.join(ROOT, "engine_v2.py")
tmp = tempfile.mkdtemp(prefix="pindeps_")

PLAN = """OUT_DIR = r%r
MODULE_NAME = "pd_mod"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {"name": "base_offset",
     "prompt": "Write base_offset() that returns the integer %d. Output ONLY the function code.",
     "tests": ["assert base_offset() == %d"]},
    {"name": "shifted",
     "prompt": "Write shifted(x) that returns x + base_offset(). base_offset() already exists in the namespace - call it; do NOT redefine it. Output ONLY the function code.",
     "tests": ["assert shifted(0) == shifted(1) - 1", "assert isinstance(shifted(2), int)"]},
]
"""
# NOTE: shifted's tests are RELATIVE on purpose — they pass with ANY base_offset value. That is the exact
# stale-green trap: change base_offset's spec and old-shifted still validates green against its own tests.

plan_path = os.path.join(tmp, "plan_pd.py")

def write_plan(offset):
    open(plan_path, "w", encoding="utf-8").write(PLAN % (tmp, offset, offset))

def build():
    env = dict(os.environ, LOCAL_OPENAI_URL="http://127.0.0.1:8089/v1/chat/completions")
    r = subprocess.run([sys.executable, ENGINE, plan_path, "openai:local", "5"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return json.loads(m.group(1)) if m else None, out

def srcs(mj):
    return {p["name"]: p["src"] for p in mj["per_function"]}

fails = []
def check(name, ok, detail=""):
    print("  %-52s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

write_plan(7)
mj1, o1 = build()
check("build 1: both functions gated green", mj1 and mj1["functions_passed"] == 2, o1[-400:] if mj1 is None else "")

mj2, o2 = build()
if mj2:
    check("build 2 (unchanged): base_offset REUSED", srcs(mj2).get("base_offset") == "pinned")
    check("build 2 (unchanged): shifted REUSED", srcs(mj2).get("shifted") == "pinned")
    check("build 2 (unchanged): zero model tokens", mj2["tok_total"] == 0, "tok=%s" % mj2["tok_total"])

write_plan(8)                                   # << the spec change: base_offset 7 -> 8
mj3, o3 = build()
if mj3:
    check("build 3 (A spec changed): base_offset regenerated", srcs(mj3).get("base_offset") in ("local", "claude"))
    check("build 3: B's pin INVALIDATED (transitive)", srcs(mj3).get("shifted") != "pinned",
          "src=%r — STALE-BUT-GREEN (the V3 §3 bug)" % srcs(mj3).get("shifted"))
    check("build 3: engine announced the invalidation", "INVALIDATED" in o3)

shutil.rmtree(tmp, ignore_errors=True)
print("\npin-deps e2e: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
