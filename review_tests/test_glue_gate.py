"""ACCEPTANCE TEST — enforcement mechanism #6: gate the glue (the last honest gap).
(reviewer build-spec #6: "a module whose GLUE entry point has no integration test is flagged".)

  1. substantive GLUE + NO INTEGRATION, under LATHE_GATE_GLUE=1 -> module REFUSED (GLUE GATE).
  2. same GLUE + an INTEGRATION block -> builds green.
  3. trivial GLUE (<= threshold lines) -> allowed even armed.
  4. flag OFF (default) -> legacy behavior, ungated glue builds.
  5. STRICT composes it: strict_defaults now includes LATHE_GATE_GLUE=1 (pure check).

Needs a local implementer for the function build (default :8089); step 5 is model-free.
Run:  python review_tests/test_glue_gate.py     (repo root)
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
    print("  %-60s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 5) STRICT composes glue-gating (pure, model-free)
from strict_mode import strict_defaults
pairs = dict(strict_defaults("1", {}))
check("STRICT arms LATHE_GATE_GLUE=1", pairs.get("LATHE_GATE_GLUE") == "1", str(pairs))

url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
up = True
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    up = "HTTP" in type(e).__name__
if not up:
    print("  (build steps SKIPPED — no implementer endpoint; STRICT-composition verified)")
    print("\nglue-gate acceptance: %s" % ("ALL PASS" if not fails else "FAILED"))
    sys.exit(0 if not fails else 1)

tmp = tempfile.mkdtemp(prefix="glue_")
# a real function + hand-written GLUE (a main() that wires it) + optional INTEGRATION
GLUE = "def run(x):\n    return add1(x) * 2\n\ndef main():\n    return run(10)\n"
INTEG = "import rp_glue\nassert rp_glue.run(3) == 8\nassert rp_glue.main() == 22\n"
PLAN = """OUT_DIR = r%r
MODULE_NAME = "rp_glue"
HEADER = ""
GLUE = %r
%s
FUNCTIONS = [{"name": "add1", "prompt": "Write add1(x): return x + 1. Output ONLY the function code.", "tests": ["assert add1(1) == 2", "assert add1(-1) == 0"]}]
"""
plan_path = os.path.join(tmp, "plan_glue.py")

def build(glue, integ, armed):
    open(plan_path, "w", encoding="utf-8").write(
        PLAN % (tmp, glue, ("INTEGRATION = %r" % integ) if integ else ""))
    for f in ("rp_glue.py", ".pins.json"):
        try:
            os.remove(os.path.join(tmp, f))
        except OSError:
            pass
    env = {k: v for k, v in os.environ.items() if k != "LATHE_GATE_GLUE"}
    env["LOCAL_OPENAI_URL"] = url
    if armed:
        env["LATHE_GATE_GLUE"] = "1"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), plan_path, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return (json.loads(m.group(1)) if m else None), out, os.path.exists(os.path.join(tmp, "rp_glue.py"))

# 1) substantive glue, no integration, armed -> REFUSED
mj, out, wrote = build(GLUE, None, armed=True)
check("armed: substantive GLUE w/o INTEGRATION is REFUSED", mj and not mj["build_ok"] and "GLUE GATE" in out, out[-300:])
check("armed: the module file is NOT written", not wrote)

# 2) same glue WITH integration -> green
mj, out, wrote = build(GLUE, INTEG, armed=True)
check("armed: GLUE + INTEGRATION builds green", mj and mj["build_ok"] and wrote, out[-300:])

# 3) trivial glue -> allowed even armed
mj, out, wrote = build("x = 1\n", None, armed=True)
check("armed: trivial GLUE is allowed", mj and mj["build_ok"], out[-300:])

# 4) flag off -> legacy (ungated glue builds)
mj, out, wrote = build(GLUE, None, armed=False)
check("flag off: ungated GLUE builds (legacy)", mj and mj["build_ok"] and wrote, out[-300:])

shutil.rmtree(tmp, ignore_errors=True)
print("\nglue-gate acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
