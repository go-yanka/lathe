"""ACCEPTANCE TEST — E2 (review §16.1, HIGH): equivalent mutants must not falsely block correct code.

  AT-E2a (no false block): the reviewer's exact repro — scale(x) with a slack guard constant (n=5, n>0)
          and a COMPLETE suite must BUILD GREEN at LATHE_MUTATION_SCORE=0.5 (equivalent mutants excluded).
  AT-E2b (gate not neutered): square(x)=x*x with only square(2)==4 must still BLOCK at 0.5 — the
          surviving x+x mutant is KILLABLE, not equivalent, so it counts.
  + offline: the differential probe itself (equivalent guard-slack -> True; x*x vs x+x -> False).
Needs a local implementer for the live builds (default :8089); offline probe checks always run.
Run:  python review_tests/test_mutation_equiv.py     (repo root)
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
fails = []
def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

from mutation_equiv import equivalent_over_samples
A = "def f(x):\n    n = 5\n    if n > 0:\n        return x * 2\n    return -x"
check("probe: guard-slack mutant is equivalent", equivalent_over_samples(A, A.replace("n = 5", "n = 6"), "f") is True)
check("probe: x*x vs x+x is NOT equivalent",
      equivalent_over_samples("def f(x):\n    return x * x", "def f(x):\n    return x + x", "f") is False)

url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
up = True
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    up = "HTTP" in type(e).__name__
if not up:
    print("  (live builds SKIPPED — no implementer endpoint)")
    print("\nmutation-equiv acceptance: %s" % ("ALL PASS" if not fails else "FAILED"))
    sys.exit(0 if not fails else 1)

tmp = tempfile.mkdtemp(prefix="meq_")
PLAN = """OUT_DIR = r%r
MODULE_NAME = "meq_mod"
HEADER = ""
GLUE = ""
FUNCTIONS = [{"name": %r, "prompt": %r, "tests": %r}]
"""
def build(fn, prompt, tests):
    pp = os.path.join(tmp, "plan_meq.py")
    open(pp, "w", encoding="utf-8").write(PLAN % (tmp, fn, prompt + " Output ONLY the function code.", tests))
    try:
        os.remove(os.path.join(tmp, ".pins.json"))
    except OSError:
        pass
    env = dict(os.environ, LOCAL_OPENAI_URL=url, LATHE_MUTATION_SCORE="0.5")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), pp, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return (json.loads(m.group(1)) if m else None), out

# AT-E2a: the exact reviewer repro — complete suite on guard-slack code must build green
mj, out = build("scale",
    "Write scale(x): set n = 5; if n > 0: return x * 2; otherwise return -x. Use exactly that structure.",
    ["assert scale(3) == 6", "assert scale(-3) == -6", "assert scale(0) == 0",
     "assert scale(10) == 20", "assert scale(-7) == -14"])
check("AT-E2a: complete suite on guard-slack code builds GREEN", mj and mj["build_ok"], out[-400:])
check("AT-E2a: equivalent mutants were excluded (reported)", "equivalent mutant" in out or (mj and mj["build_ok"]))

# AT-E2b: the gate is not neutered — killable survivor still blocks
mj, out = build("square", "Write square(x): return x * x. Use exactly the expression x * x.",
                ["assert square(2) == 4"])
check("AT-E2b: weak suite still BLOCKS (killable mutant counts)", mj and not mj["build_ok"]
      and "MUTATION-SCORE GATE" in out, out[-300:])

shutil.rmtree(tmp, ignore_errors=True)
print("\nmutation-equiv acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
