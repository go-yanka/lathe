"""ACCEPTANCE — issue #47: a TEST-KIND gate refusal is SELF-HEALING, not a dead end.

The kind detector is a substring heuristic that false-refuses genuinely-thorough tests, and because it refuses
BEFORE generation (tries=0, no model call) it historically banked NO evidence — so the auto-repair loop then
skipped ("no banked failures found for this plan"). The fix banks a SYNTHETIC evidence record (+ actionable
guidance) at the refusal, so the analyst-repair loop can engage and propose the missing test kind.

Model-free: the gate refuses before any generation, so no implementer endpoint is needed — deterministic.

  Run:  python review_tests/test_kind_gate_repairable.py     (repo root)
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
fails = []


def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


# tokenize-style tests that are genuinely edge-shaped (single token, nesting) but contain NONE of the detector's
# 'edge' substrings ('== 0', "'' ", '[]', 'none', 'empty', ' -1', ...) — so the heuristic false-refuses 'edge'.
FUNCS = ('[{"name": "to_rpn", "kinds": ["edge"], '
         '"prompt": "Write to_rpn(expr): tokenize a simple + and * expression left to right. Output ONLY the function code.", '
         '"tests": ["assert to_rpn(\'a\') == [\'a\']", '
         '"assert to_rpn(\'a+b\') == [\'a\', \'b\', \'+\']", '
         '"assert to_rpn(\'a*b+c\') == [\'a\', \'b\', \'*\', \'c\', \'+\']"]}]')
PLAN = 'OUT_DIR = r%r\nMODULE_NAME = "rpn"\nHEADER = ""\nFUNCTIONS = %s\n'

# 0) sanity (model-free): the detector really does NOT see 'edge' in these tests (so the gate WILL refuse)
import test_kind  # noqa: E402
_tests = ["assert to_rpn('a') == ['a']", "assert to_rpn('a+b') == ['a', 'b', '+']",
          "assert to_rpn('a*b+c') == ['a', 'b', '*', 'c', '+']"]
_kinds = test_kind.detect_kinds(_tests)
check("detector false-refuses: 'edge' NOT detected in genuinely-edge tests", "edge" not in _kinds, str(_kinds))

_WS_ROOT = (os.environ.get("LATHE_WORKSPACE_ROOT")
            or ("C:/lathe-workspaces" if os.name == "nt" else os.path.join(os.path.expanduser("~"), ".lathe", "workspaces")))
os.makedirs(_WS_ROOT, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="test_i47_", dir=_WS_ROOT).replace("\\", "/")
plan_path = os.path.join(tmp, "plan_rpn.py")
open(plan_path, "w", encoding="utf-8").write(PLAN % (tmp, FUNCS))

# Run the ENGINE directly with the kind gate ARMED — it refuses `to_rpn` BEFORE generation (no model call), so
# this is deterministic and model-free (avoids the STRICT workflow's RTM/analyst wrapper, which is out of scope).
env = dict(os.environ, LATHE_TEST_KIND="1")
r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), plan_path, "openai:local", "5"],
                   cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
out = (r.stdout or "") + (r.stderr or "")
check("kind gate refuses the unit (TEST-KIND GATE)", "TEST-KIND GATE" in out, out[-400:])

# THE FIX: a synthetic evidence record is banked, so the repair loop is no longer a dead end
faildir = os.path.join(tmp, "_fn_fails")
reasons = glob.glob(os.path.join(faildir, "to_rpn*.reason.txt"))
banked_txt = ""
if reasons:
    banked_txt = open(reasons[0], encoding="utf-8").read()
check("refusal BANKS a synthetic evidence record (repair can now engage)", bool(reasons), "no _fn_fails/*.reason.txt banked")
check("banked reason is actionable (names the missing kind + 'add a test')",
      ("edge" in banked_txt.lower()) and ("add a test" in banked_txt.lower()), banked_txt[:200])

shutil.rmtree(tmp, ignore_errors=True)
print("\ntest-kind repairable (#47) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
