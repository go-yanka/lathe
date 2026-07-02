"""ACCEPTANCE TEST — enforcement mechanism #5: required KIND of test per contract.
(reviewer build-spec #5: "an enhancement plan with no property test for a declared invariant is refused".)

  1. detect_kinds (pure): recognizes property / roundtrip / edge / error / example shapes.
  2. a function that DECLARES kinds:['property'] but ships only example asserts -> REFUSED under LATHE_TEST_KIND=1.
  3. the same function WITH a property test -> builds green.
  4. plan-level TEST_KINDS applies to every function.
  5. flag off (default) -> legacy, no kind requirement.
  6. STRICT composes it: strict_defaults includes LATHE_TEST_KIND=1 (pure).
Needs a local implementer for the builds (default :8089); steps 1 + 6 are model-free.
Run:  python review_tests/test_test_kind.py     (repo root)
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
from test_kind import detect_kinds, kind_gaps
from strict_mode import strict_defaults

fails = []
def check(name, ok, detail=""):
    print("  %-60s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 1) pure detection
check("detect: property", "property" in detect_kinds(["assert all(f(i) >= 0 for i in range(5))"]))
check("detect: roundtrip", "roundtrip" in detect_kinds(["assert decode(encode(x)) == x"]))
check("detect: edge", "edge" in detect_kinds(["assert f([]) == 0"]))
check("detect: example only has no property", "property" not in detect_kinds(["assert f(2) == 4"]))
# 6) STRICT composition
check("STRICT arms LATHE_TEST_KIND=1", dict(strict_defaults("1", {})).get("LATHE_TEST_KIND") == "1")
check("kind_gaps opt-in off by default", kind_gaps(None, ["property"], set()) == [])

url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
up = True
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    up = "HTTP" in type(e).__name__
if not up:
    print("  (build steps SKIPPED — no implementer endpoint; detection + STRICT verified)")
    print("\ntest-kind acceptance: %s" % ("ALL PASS" if not fails else "FAILED"))
    sys.exit(0 if not fails else 1)

tmp = tempfile.mkdtemp(prefix="tk_")
def build(tests, kinds, armed, plan_kinds=None):
    pp = os.path.join(tmp, "plan_tk.py")
    fn = "{'name': 'sq', 'prompt': 'Write sq(x): return x*x. Output ONLY the function code.', 'tests': %r, 'kinds': %r}" % (tests, kinds)
    body = "OUT_DIR = r%r\nMODULE_NAME = 'tk_mod'\nHEADER = ''\nGLUE = ''\nFUNCTIONS = [%s]\n" % (tmp, fn)
    if plan_kinds:
        body += "TEST_KINDS = %r\n" % plan_kinds
    open(pp, "w", encoding="utf-8").write(body)
    for f in ("tk_mod.py", ".pins.json"):
        try:
            os.remove(os.path.join(tmp, f))
        except OSError:
            pass
    env = {k: v for k, v in os.environ.items() if k != "LATHE_TEST_KIND"}
    env["LOCAL_OPENAI_URL"] = url
    if armed:
        env["LATHE_TEST_KIND"] = "1"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), pp, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return (json.loads(m.group(1)) if m else None), out

EX = ["assert sq(2) == 4", "assert sq(3) == 9"]                      # example only
PROP = EX + ["assert all(sq(i) >= 0 for i in range(-3, 4))"]        # + a property test

# 2) declares property, ships only examples, armed -> REFUSED
mj, out = build(EX, ["property"], armed=True)
check("armed: missing declared 'property' kind is REFUSED", mj and not mj["build_ok"] and "TEST-KIND GATE" in out, out[-250:])

# 3) with the property test -> green
mj, out = build(PROP, ["property"], armed=True)
check("armed: property test present -> builds green", mj and mj["build_ok"], out[-250:])

# 4) plan-level TEST_KINDS applies
mj, out = build(EX, None, armed=True, plan_kinds=["property"])
check("armed: plan-level TEST_KINDS enforced too", mj and not mj["build_ok"] and "TEST-KIND GATE" in out, out[-250:])

# 5) flag off -> legacy
mj, out = build(EX, ["property"], armed=False)
check("flag off -> legacy (no kind requirement)", mj and mj["build_ok"], out[-250:])

shutil.rmtree(tmp, ignore_errors=True)
print("\ntest-kind acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
