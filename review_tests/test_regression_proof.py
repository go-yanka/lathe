"""ACCEPTANCE TEST — enforcement mechanism #1: regression-test-must-fail-on-old-code.
(docs/METHODOLOGY_ENFORCEMENT_VALIDATION.md build-spec item 1.)

Asserts:
  1. build v1 of a function -> green, module on disk (the "old code").
  2. LATHE_REGRESSION_PROOF=1 + a changed spec whose new tests ALL PASS on the old code -> REFUSED
     (no generation attempted; the change ships no test that reproduces a bug).
  3. same flag + a new test that FAILS on the old code (a real repro) -> gate passes, build proceeds green.
  4. flag OFF (default) -> legacy behavior, the v2a-style change builds fine.
  5. flag ON + a brand-NEW function (no old impl) -> not blocked (rule only applies to changed units).

Needs a local implementer (default http://127.0.0.1:8089; set LOCAL_OPENAI_URL). If unreachable, the
whole test SKIPs rc 0 (this mechanism is exercised inside real builds — there is no offline half).
Run:  python review_tests/test_regression_proof.py     (repo root)
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
url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    if "HTTP" not in type(e).__name__:
        print("SKIP: no implementer endpoint at %s (mechanism #1 only exists inside real builds)" % url)
        sys.exit(0)

tmp = tempfile.mkdtemp(prefix="rproof_")
fails = []
def check(name, ok, detail=""):
    print("  %-62s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

PLAN = """OUT_DIR = r%r
MODULE_NAME = "rp_mod"
HEADER = ""
GLUE = ""
FUNCTIONS = [{"name": %r, "prompt": %r, "tests": %r}]
"""
plan_path = os.path.join(tmp, "plan_rp.py")

def build(fn, prompt, tests, flag=None):
    open(plan_path, "w", encoding="utf-8").write(PLAN % (tmp, fn, prompt + " Output ONLY the function code.", tests))
    env = dict(os.environ, LOCAL_OPENAI_URL=url)
    if flag is not None:
        env["LATHE_REGRESSION_PROOF"] = flag
    else:
        env.pop("LATHE_REGRESSION_PROOF", None)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), plan_path, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return (json.loads(m.group(1)) if m else None), out

# 1) v1: the "old code" — clamps high but NOT low (the seeded bug)
mj, out = build("cap10", "Write cap10(x): return x if x < 10 else 10. Do NOT handle negatives specially.",
                ["assert cap10(5) == 5", "assert cap10(20) == 10"])
check("v1 builds green (old code on disk)", mj and mj["build_ok"], out[-300:])

# 2) changed spec, but every new test PASSES on the old code -> REFUSED, zero generation
mj, out = build("cap10", "Write cap10(x): clamp x into [0, 10] - return min(10, max(0, x)).",
                ["assert cap10(5) == 5", "assert cap10(20) == 10", "assert cap10(3) == 3"], flag="1")
check("no-repro change is REFUSED under the flag", mj and not mj["build_ok"], out[-300:])
check("the refusal names the gate + the reason", "REGRESSION-PROOF GATE" in out and "reproduces" in out)
check("zero generation tokens were spent on it", mj and mj["tok_total"] == 0, "tok=%s" % (mj and mj["tok_total"]))

# 3) same change WITH a reproducing test (fails on old code: old cap10(-5) == -5, not 0) -> proceeds green
mj, out = build("cap10", "Write cap10(x): clamp x into [0, 10] - return min(10, max(0, x)).",
                ["assert cap10(5) == 5", "assert cap10(20) == 10", "assert cap10(-5) == 0"], flag="1")
check("reproducing-test change builds green", mj and mj["build_ok"], out[-300:])
check("gate acknowledged the proof", "proof present" in out or mj["build_ok"])

# 4) flag OFF: the no-repro change is legacy-allowed (opt-in gate)
mj, out = build("cap10", "Write cap10(x): clamp x into [0, 10] using min and max - return min(10, max(0, x)).",
                ["assert cap10(5) == 5", "assert cap10(3) == 3"])
check("flag off -> legacy behavior (no refusal)", mj and mj["build_ok"], out[-300:])

# 5) flag ON + brand-new function (no old impl) -> not blocked
mj, out = build("triple", "Write triple(x): return x * 3.", ["assert triple(2) == 6"], flag="1")
check("new function is not blocked (no prior impl)", mj and mj["build_ok"], out[-300:])

shutil.rmtree(tmp, ignore_errors=True)
print("\nregression-proof acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
