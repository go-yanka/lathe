"""ACCEPTANCE TEST — the reproducibility claim, validated end-to-end and scoped honestly (task #46).

Lathe claims TWO different things; this test measures both and refuses to conflate them:
  A. PINNED-REBUILD reproducibility (the guarantee): with pins present, a rebuild is byte-identical
     with ZERO model calls — build×3, plus a clean-checkout simulation (fresh dir, same plan+pins).
  B. REGENERATION determinism (NOT guaranteed): delete the pins and regenerate — the output may be
     different-but-test-passing code. This test MEASURES it and only records the outcome; asserting
     identity here would be dishonest (models are stochastic).
  C. The pin is honest: change the SPEC -> the pin key changes -> the function regenerates.

Needs a local implementer (default :8089); SKIPs rc 0 without one.
Run:  python review_tests/test_reproducibility.py     (repo root)
"""
import hashlib
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
        print("SKIP: no implementer endpoint at %s" % url)
        sys.exit(0)

tmp = tempfile.mkdtemp(prefix="repro_")
fails = []
def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

PLAN = """OUT_DIR = r%r
MODULE_NAME = "rp_repro"
HEADER = ""
GLUE = ""
FUNCTIONS = [{"name": "csv_head",
    "prompt": "Write csv_head(line): return the text before the first comma of the string; no comma -> the whole string; None/empty -> ''. %s Output ONLY the function code.",
    "tests": ["assert csv_head('a,b,c') == 'a'", "assert csv_head('abc') == 'abc'", "assert csv_head('') == ''", "assert csv_head(None) == ''"]}]
"""

def build(where, note=""):
    pp = os.path.join(where, "plan_r.py")
    open(pp, "w", encoding="utf-8").write(PLAN % (where, note))
    env = dict(os.environ, LOCAL_OPENAI_URL=url)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "engine_v2.py"), pp, "openai:local", "5"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", r.stdout or "", re.S)
    mj = json.loads(m.group(1)) if m else None
    mod = os.path.join(where, "rp_repro.py")
    h = hashlib.sha256(open(mod, "rb").read()).hexdigest() if os.path.exists(mod) else ""
    return mj, h

# A) build once, then rebuild x3: byte-identical module, zero model calls each time
mj, h0 = build(tmp)
check("initial build green", mj and mj["build_ok"])
ok_reuse, ok_bytes, ok_tokens = True, True, True
for i in range(3):
    mj, h = build(tmp)
    ok_reuse &= (mj and mj["per_function"][0]["src"] == "pinned")
    ok_bytes &= (h == h0)
    ok_tokens &= (mj and mj["tok_total"] == 0)
check("rebuild x3: every pass REUSED from pin", ok_reuse)
check("rebuild x3: module byte-identical (sha256)", ok_bytes)
check("rebuild x3: ZERO model tokens", ok_tokens)

# A2) clean-checkout simulation: fresh dir + same plan + same pins -> identical, no model call
clone = tempfile.mkdtemp(prefix="repro_clone_")
shutil.copy(os.path.join(tmp, ".pins.json"), os.path.join(clone, ".pins.json"))
mj, h = build(clone)
check("clean checkout + pins: REUSED, byte-identical", mj and mj["per_function"][0]["src"] == "pinned" and h == h0,
      "src=%r same=%s" % (mj and mj["per_function"][0]["src"], h == h0))

# B) regeneration determinism: delete pins, regenerate — MEASURED, not asserted
os.remove(os.path.join(tmp, ".pins.json"))
mj, h1 = build(tmp)
check("regeneration (pins deleted) still gates green", mj and mj["build_ok"])
same = (h1 == h0)
print("  [measured] regenerated code byte-identical to original: %s  <- NOT a guarantee; recorded honestly" % same)

# C) the pin is honest: change the spec -> regenerate (no stale reuse)
mj, _ = build(tmp, "Treat a leading comma as an empty first field.")
check("spec change -> pin miss -> fresh generation (not 'pinned')",
      mj and mj["per_function"][0]["src"] != "pinned")

shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(clone, ignore_errors=True)
print("\nreproducibility acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
