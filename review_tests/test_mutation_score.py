"""ACCEPTANCE TEST — enforcement mechanism #3: a real mutation-SCORE threshold (comprehensiveness measured).
(docs/METHODOLOGY_ENFORCEMENT_VALIDATION.md build-spec item 3: "a suite that passes but kills <X% of
mutants BLOCKS the build".)

  1. weak suite: square(x) with only `square(2)==4` — passes the gate, but the x+x mutant also returns 4,
     so the suite kills 0 mutants -> build BLOCKED at LATHE_MUTATION_SCORE=0.5, code NOT pinned, and the
     weak-tests reason is banked to _fn_fails (failure-as-asset).
  2. strong suite: add `square(3)==9` — kills the mutants -> builds green under the same threshold.
  3. flag off -> the weak suite builds fine (legacy; the gate is opt-in / strict-mode-forced).
  4. offline unit: mutate_code produces the discriminating x+x mutant deterministically (LLM-free).

Needs a local implementer for 1-3 (default :8089). Step 4 always runs.
Run:  python review_tests/test_mutation_score.py     (repo root)
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
    print("  %-62s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 4) offline: the mutator is deterministic and produces the discriminating mutant
from mutation_score import mutate_code, mutation_gate
v = mutate_code("def square(x):\n    return x * x", 8)
check("mutator emits the x+x mutant (deterministic, LLM-free)", any("x + x" in m for m in v))
check("gate blocks a 0-kill suite at 0.5", mutation_gate("0.5", 0, 1)[0] is True)
check("gate passes a full-kill suite at 0.5", mutation_gate("0.5", 1, 1)[0] is False)

url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
up = True
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    up = "HTTP" in type(e).__name__
if not up:
    print("  (live steps SKIPPED — no implementer endpoint)")
    print("\nmutation-score acceptance: %s" % ("ALL PASS" if not fails else "FAILED"))
    sys.exit(0 if not fails else 1)

tmp = tempfile.mkdtemp(prefix="mut_")
PLAN = """OUT_DIR = r%r
MODULE_NAME = "mut_mod"
HEADER = ""
GLUE = ""
FUNCTIONS = [{"name": "square",
    "prompt": "Write square(x): return x * x. Use exactly the expression x * x. Output ONLY the function code.",
    "tests": %s}]
"""
plan_path = os.path.join(tmp, "plan_mut.py")

def build(tests, score=None):
    open(plan_path, "w", encoding="utf-8").write(PLAN % (tmp, tests))
    try:
        os.remove(os.path.join(tmp, ".pins.json"))
    except OSError:
        pass
    env = {k: v for k, v in os.environ.items() if k != "LATHE_MUTATION_SCORE"}
    env["LOCAL_OPENAI_URL"] = url
    if score is not None:
        env["LATHE_MUTATION_SCORE"] = score
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), plan_path, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return (json.loads(m.group(1)) if m else None), out

# 1) weak suite blocked at 0.5 (x+x survives square(2)==4)
mj, out = build('["assert square(2) == 4"]', score="0.5")
check("weak suite BLOCKS the build (mutants survive)", mj and not mj["build_ok"], out[-300:])
check("the block names the gate + kill count", "MUTATION-SCORE GATE" in out and "kill only" in out)
check("weak-tests reason banked to _fn_fails", os.path.exists(os.path.join(tmp, "_fn_fails")) and
      any("mutation gate" in open(os.path.join(tmp, "_fn_fails", f), encoding="utf-8", errors="replace").read()
          for f in os.listdir(os.path.join(tmp, "_fn_fails")) if f.endswith(".reason.txt")))

# 2) strong suite passes the same threshold
mj, out = build('["assert square(2) == 4", "assert square(3) == 9", "assert square(0) == 0"]', score="0.5")
check("strong suite builds green under the same threshold", mj and mj["build_ok"], out[-300:])
check("score reported", "mutation score ok" in out or (mj and mj["build_ok"]))

# 3) flag off -> weak suite is legacy-allowed
mj, out = build('["assert square(2) == 4"]')
check("flag off -> legacy (weak suite builds)", mj and mj["build_ok"], out[-300:])

shutil.rmtree(tmp, ignore_errors=True)
print("\nmutation-score acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
