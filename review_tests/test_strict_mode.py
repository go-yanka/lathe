"""ACCEPTANCE TEST — LATHE_STRICT=1: the SDLC enforcement umbrella forces EVERY proof mechanism for ALL
development (new + enhancement), no picking and choosing.

Asserts, in order (each proves one constituent is actually forced by the umbrella alone —
no other enforcement env var is set at any point):
  1. strict + plan WITHOUT CRITERIA            -> REFUSED (traceability is mandatory).
  2. strict + criteria, tests NOT acknowledged -> REFUSED by the test-ack gate.
  3. strict + acked, NEW function whose tests a trivial stub satisfies -> BLOCKED by the mutation probe.
  4. strict + acked, real tests               -> builds green (v1 on disk).
  5. strict + CHANGED function (enhancement) whose new tests all pass on the old code -> REFUSED
     (regression-proof applies to enhancements, not just bug fixes).
  6. strict + a reproducing/behavior-changing test -> green.
  7. no flag -> the same no-criteria plan builds fine (strict is opt-in; default behavior unchanged).

Needs a local implementer for the green builds (default :8089). If unreachable: steps 1-3 still run
(they refuse BEFORE generation); 4-7 are skipped.
Run:  python review_tests/test_strict_mode.py     (repo root)
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
model_up = True
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    model_up = "HTTP" in type(e).__name__

tmp = tempfile.mkdtemp(prefix="strict_")
fails = []
def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

PLAN = """OUT_DIR = r%r
MODULE_NAME = "st_mod"
HEADER = ""
GLUE = ""
FUNCTIONS = [{"name": %r, "prompt": %r, "tests": %r}]
%s
"""
CRIT = "CRITERIA = [{'id': 'AC-1', 'text': 'the declared behavior', 'tests': [%r]}]"
plan_path = os.path.join(tmp, "plan_st.py")

def build(fn, prompt, tests, criteria=True, strict=True, ack=False):
    open(plan_path, "w", encoding="utf-8").write(
        PLAN % (tmp, fn, prompt + " Output ONLY the function code.", tests, (CRIT % fn) if criteria else ""))
    if ack:
        subprocess.run([sys.executable, os.path.join(ROOT, "lathe.py"), "ack", plan_path, "--yes"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    env = {k: v for k, v in os.environ.items()
           if k not in ("LATHE_TEST_ACK", "LATHE_REGRESSION_PROOF", "LATHE_LINT_SPEC", "LATHE_STRICT")}
    env["LOCAL_OPENAI_URL"] = url
    if strict:
        env["LATHE_STRICT"] = "1"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), plan_path, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return (json.loads(m.group(1)) if m else None), out, r.returncode

# 1) strict + no CRITERIA -> refused
mj, out, rc = build("inc", "Write inc(x): return x+1.", ["assert inc(1) == 2"], criteria=False)
check("strict: plan without CRITERIA is REFUSED", rc != 0 and "CRITERIA" in out, out[-200:])

# 2) strict + criteria but un-acked tests -> refused by the (umbrella-forced) test-ack gate
mj, out, rc = build("inc", "Write inc(x): return x+1.", ["assert inc(1) == 2"])
check("strict: un-acked tests are REFUSED (test-ack forced)", rc != 0 and "TEST-ACK" in out, out[-200:])

# 3) strict + acked but stub-satisfiable tests -> blocked by the (forced) mutation probe
mj, out, rc = build("noop", "Write noop(x): return None.", ["assert noop(5) is None"], ack=True)
check("strict: stub-satisfiable tests are BLOCKED (lint forced)", rc != 0 and "inadequate tests" in out, out[-200:])

if model_up:
    # 4) compliant new function -> green
    mj, out, rc = build("inc", "Write inc(x): return x+1.", ["assert inc(1) == 2", "assert inc(-1) == 0"], ack=True)
    check("strict: compliant new function builds green", mj and mj["build_ok"], out[-300:])
    # 5) ENHANCEMENT whose new tests all pass on old code -> refused (proof applies to all changes)
    mj, out, rc = build("inc", "Write inc(x): return x+1 (handle any int).",
                        ["assert inc(1) == 2", "assert inc(-1) == 0", "assert inc(10) == 11"], ack=True)
    check("strict: no-proof ENHANCEMENT is REFUSED", mj and not mj["build_ok"] and "REGRESSION-PROOF" in out, out[-300:])
    # 6) enhancement with a behavior-proving test (old inc has no clamp; new spec clamps at 100) -> green
    mj, out, rc = build("inc", "Write inc(x): return min(x+1, 100) - increments but caps at 100.",
                        ["assert inc(1) == 2", "assert inc(200) == 100"], ack=True)
    check("strict: proof-carrying enhancement builds green", mj and mj["build_ok"], out[-300:])
    # 7) default (no flag): the same no-criteria plan builds fine
    mj, out, rc = build("dbl", "Write dbl(x): return x*2.", ["assert dbl(2) == 4", "assert dbl(0) == 0"],
                        criteria=False, strict=False)
    check("no flag: default behavior unchanged (opt-in)", mj and mj["build_ok"], out[-300:])
else:
    print("  (steps 4-7 SKIPPED — no implementer endpoint; the three refusal paths above are model-free)")

shutil.rmtree(tmp, ignore_errors=True)
print("\nstrict-mode acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
