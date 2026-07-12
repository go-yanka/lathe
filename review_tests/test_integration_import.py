"""ACCEPTANCE — issue #44: INTEGRATION can reference the module's GLUE/function symbols WITHOUT an `import`.

The engine runs the INTEGRATION script STANDALONE, so it needs the module's symbols in scope — but the plan
validator (correctly) bans every `import` inside the plan. That catch-22 made GLUE+INTEGRATION unbuildable
through the validated path except via LATHE_TRUST_PLAN=1 (a full security downgrade). The fix: the engine
auto-prepends `from <MODULE_NAME> import *` to the generated itest, so INTEGRATION needs no import and the
validator stays strict.

This proves a GLUE symbol (`evaluate`) is integration-tested through the VALIDATED path (`lathe build`, no
LATHE_TRUST_PLAN). The plan has ONE trivial function so the validator accepts it and the implementer barely
works; the build steps SKIP if no implementer endpoint is up (same convention as test_glue_gate.py).

  Run:  python review_tests/test_integration_import.py     (repo root)
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


# A trivial function + a GLUE evaluate() that composes it + an INTEGRATION that calls evaluate() UNQUALIFIED
# and with NO import (the exact shape #44 unblocks).
FUNCS = ('[{"name": "add_ints", "prompt": "Write add_ints(a, b) that returns a + b. Output ONLY the function code.", '
         '"tests": ["assert add_ints(2, 3) == 5", "assert add_ints(-1, 1) == 0"]}]')
GLUE = "def evaluate(expr):\n    total = 0\n    for p in expr.split('+'):\n        total = add_ints(total, int(p))\n    return total\n"
INTEG = "assert evaluate('2+3') == 5\nassert evaluate('10+20+30') == 60\nprint('itest ok: evaluate in scope with no import')\n"
PLAN = 'OUT_DIR = r%r\nMODULE_NAME = "calc"\nHEADER = ""\nFUNCTIONS = %s\nGLUE = %r\nINTEGRATION = %r\n'

# OUT_DIR must live under the sanctioned WORKSPACE_ROOT (the validator refuses an OUT_DIR that escapes the
# working tree / workspace root — a correct guard), NOT system temp.
_WS_ROOT = (os.environ.get("LATHE_WORKSPACE_ROOT")
            or ("C:/lathe-workspaces" if os.name == "nt" else os.path.join(os.path.expanduser("~"), ".lathe", "workspaces")))
os.makedirs(_WS_ROOT, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="test_i44_", dir=_WS_ROOT).replace("\\", "/")
plan_path = os.path.join(tmp, "plan_calc.py")
open(plan_path, "w", encoding="utf-8").write(PLAN % (tmp, FUNCS, GLUE, INTEG))

# 1) MODEL-FREE: the validator ACCEPTS the no-import INTEGRATION, and STILL bans a real import (not weakened).
import plan_validator  # noqa: E402
v = plan_validator.is_valid_plan(open(plan_path, encoding="utf-8").read())
check("validator accepts GLUE+INTEGRATION with no import (buildable path)", v.get("ok"), v.get("reason", ""))
v_bad = plan_validator.is_valid_plan(PLAN % (tmp, FUNCS, GLUE, "import os\n" + INTEG))
check("validator STILL bans a real import in INTEGRATION (fix didn't weaken it)", not v_bad.get("ok"), str(v_bad))

# 2) BUILD through the VALIDATED path (`lathe build`) with LATHE_TRUST_PLAN UNSET -> INTEGRATION must PASS,
#    which can only happen if the engine auto-imported the module (before the fix: NameError -> integration FAIL).
url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
    up = True
except Exception as e:
    up = "HTTP" in type(e).__name__
if not up:
    shutil.rmtree(tmp, ignore_errors=True)
    print("  (build step SKIPPED — no implementer endpoint; validator contract verified)")
    print("\nintegration-import (#44) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
    sys.exit(0 if not fails else 1)

env = {k: val for k, val in os.environ.items() if k != "LATHE_TRUST_PLAN"}
env["LOCAL_OPENAI_URL"] = url
r = subprocess.run([sys.executable, os.path.join(ROOT, "lathe.py"), "build", plan_path],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=300)
out = (r.stdout or "") + (r.stderr or "")
m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
mj = json.loads(m.group(1)) if m else None
check("build produced metrics (validated path, no TRUST_PLAN)", mj is not None, out[-500:])
check("INTEGRATION PASSES (engine auto-imported the module)", bool(mj) and str(mj.get("integration", "")).startswith("PASS"),
      (mj or {}).get("integration"))
_ip = os.path.join(tmp, "_itest_calc.py")
itest_body = open(_ip, encoding="utf-8").read() if os.path.exists(_ip) else ""
check("generated itest auto-imports the module (from calc import *)", "from calc import *" in itest_body, itest_body[:200])

shutil.rmtree(tmp, ignore_errors=True)
print("\nintegration-import (#44) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
