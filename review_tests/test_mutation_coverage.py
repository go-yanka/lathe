"""ACCEPTANCE TEST — E1 (review §16.1) + E3 + E4: the remaining v2.2.0 edge fixes.

  AT-E1a: boolean function (a and b) with a weak suite now produces >=1 mutant and BLOCKS at 0.5
          (operator broadening: bool/membership/is/str-const are mutable now).
  AT-E1b: a truly unmutatable function under an ARMED gate emits the loud 'unmeasurable' warning and the
          `mutation_unmeasured` ledger flag — never a silent pass.
  AT-E3 : an ARTIFACTS-only plan under LATHE_STRICT=1 is REFUSED with the explicit not-gateable message
          (wording now matches code).
  AT-E4 : a "fix" that RENAMES the changed function, whose new tests all pass on the old implementation,
          is still REFUSED under LATHE_REGRESSION_PROOF=1 (rename is not a proof).
Needs a local implementer (default :8089) for E1a/E1b/E4; E3 refuses before generation (model-free).
Run:  python review_tests/test_mutation_coverage.py     (repo root)
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

# offline: broadened operators actually mutate the previously-unmutable shapes
from mutation_score import mutate_code
check("operators: boolean and->or mutant exists", any("a or b" in m for m in mutate_code("def f(a, b):\n    return a and b", 10)))
check("operators: membership in->not in mutant exists", any("not in" in m for m in mutate_code("def f(x, s):\n    return x in s", 10)))
check("operators: is None -> is not None mutant exists", any("is not None" in m for m in mutate_code("def f(x):\n    return x is None", 10)))

tmp = tempfile.mkdtemp(prefix="mcov_")
PLAN = """OUT_DIR = r%r
MODULE_NAME = "mc_mod"
HEADER = ""
GLUE = ""
FUNCTIONS = [{"name": %r, "prompt": %r, "tests": %r}]
%s
"""
def build(fn, prompt, tests, env_extra, criteria="", artifacts_only=False):
    pp = os.path.join(tmp, "plan_mc.py")
    if artifacts_only:
        open(pp, "w", encoding="utf-8").write(
            "OUT_DIR = r%r\nMODULE_NAME = 'mc_art'\nHEADER = ''\nGLUE = ''\nFUNCTIONS = []\n"
            "ARTIFACTS = [{'path': 'x.txt', 'prompt': 'write hello', 'tests': ['assert True']}]\n" % tmp)
    else:
        open(pp, "w", encoding="utf-8").write(PLAN % (tmp, fn, prompt + " Output ONLY the function code.", tests, criteria))
    env = {k: v for k, v in os.environ.items()
           if k not in ("LATHE_MUTATION_SCORE", "LATHE_STRICT", "LATHE_REGRESSION_PROOF", "LATHE_TEST_ACK", "LATHE_LINT_SPEC")}
    env["LOCAL_OPENAI_URL"] = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
    env.update(env_extra)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), pp, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
    return (json.loads(m.group(1)) if m else None), out, r.returncode

# AT-E3 first (model-free)
mj, out, rc = build(None, None, None, {"LATHE_STRICT": "1"}, artifacts_only=True)
check("AT-E3: ARTIFACTS-only plan under STRICT is REFUSED", rc != 0 and "ARTIFACTS-only" in out, out[-250:])

url = os.environ.get("LOCAL_OPENAI_URL", "http://127.0.0.1:8089/v1/chat/completions")
up = True
try:
    urllib.request.urlopen(url.replace("/chat/completions", "/models"), timeout=4)
except Exception as e:
    up = "HTTP" in type(e).__name__
# AT-E1a: deterministic (no model) — a weak suite on a boolean fn now yields a KILLABLE survivor and blocks
from mutation_score import mutation_gate
def _kills(code, name, tests):
    muts = mutate_code(code, 8)
    killed = 0
    for m in muts:
        ns = {}
        try:
            exec(m, ns)
            ok = True
            for t in tests:
                exec(t, ns)
        except Exception:
            ok = False
        killed += 0 if ok else 1   # a test raising/failing on the mutant = mutant killed
    return killed, len(muts)
k, t = _kills("def both(a, b):\n    return a and b", "both", ["assert both(True, True) == True"])
check("AT-E1a: boolean fn yields mutants + a killable survivor (broadened ops)", t >= 1 and k < t, "killed=%d total=%d" % (k, t))
check("AT-E1a: the weak boolean suite BLOCKS at 0.5", mutation_gate("0.5", k, t)[0] is True, "k=%d t=%d" % (k, t))

if up:
    # AT-E1b: truly unmutatable fn -> loud warning + ledger flag, not a silent pass
    try:
        os.remove(os.path.join(tmp, ".pins.json"))
    except OSError:
        pass
    mj, out, rc = build("ident", "Write ident(x): return x.", ["assert ident(7) == 7", "assert ident('a') == 'a'"],
                        {"LATHE_MUTATION_SCORE": "0.5"})
    check("AT-E1b: unmeasurable emits the loud warning", "unmeasurable" in out, out[-300:])
    check("AT-E1b: mutation_unmeasured ledger flag set", mj and mj.get("mutation_unmeasured") == ["ident"],
          "flag=%r" % (mj and mj.get("mutation_unmeasured")))
    check("AT-E1b: build itself still green (warn, not block)", mj and mj["build_ok"])
    # AT-E4: rename bypass refused — build v1 as parse_v1, then "fix" by renaming to parse_v2
    try:
        os.remove(os.path.join(tmp, ".pins.json"))
    except OSError:
        pass
    mj, out, rc = build("parse_v1", "Write parse_v1(s): return s.strip().", ["assert parse_v1(' a ') == 'a'"], {})
    check("AT-E4 setup: v1 builds green", mj and mj["build_ok"], out[-200:])
    mj, out, rc = build("parse_v2", "Write parse_v2(s): return s.strip().", ["assert parse_v2(' a ') == 'a'"],
                        {"LATHE_REGRESSION_PROOF": "1"})
    check("AT-E4: rename with no reproducing test is REFUSED",
          mj and not mj["build_ok"] and "possible rename" in out, out[-300:])
else:
    print("  (live steps SKIPPED — no implementer endpoint; AT-E3 + operator checks verified)")

shutil.rmtree(tmp, ignore_errors=True)
print("\nmutation-coverage acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
