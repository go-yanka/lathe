"""ACCEPTANCE TEST — the env-var SURFACE + anti-drift gate (PR#1 CLI-review #1).

  1. extract_env_vars / env_drift (pure).
  2. LIVE: env_catalog.REGISTRY documents every env var the core code actually reads (the real drift guard) —
     the same check qa/env_drift_gate.py runs, asserted here so a new undocumented var fails CI.
Offline. Run:  python review_tests/test_env_drift.py      (repo root)
"""
import glob
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INNER = os.path.join(ROOT, "projects", "agentic-harness")
sys.path.insert(0, os.path.join(INNER, "tools"))
from env_logic import extract_env_vars, env_drift

fails = []
def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 1) pure functions
src = "a=os.environ.get('LATHE_STRICT'); b=os.getenv('HARNESS_MODEL'); c=os.environ['LOCAL_OPENAI_URL']"
check("extract: all access forms, sorted+unique",
      extract_env_vars(src) == ['HARNESS_MODEL', 'LATHE_STRICT', 'LOCAL_OPENAI_URL'])
check("extract: non-str -> []", extract_env_vars(None) == [])
d = env_drift(['A', 'B', 'C'], ['A', 'B'], [])
check("drift: undocumented surfaced", d['undocumented'] == ['C'])
check("drift: ignore excludes", env_drift(['A', 'PATH'], ['A'], ['PATH'])['undocumented'] == [])

# 2) LIVE — the registry documents every env var the core code reads
spec = importlib.util.spec_from_file_location("env_catalog", os.path.join(ROOT, "env_catalog.py"))
ec = importlib.util.module_from_spec(spec); spec.loader.exec_module(ec)
_OS = {"PATH", "HOME", "USERPROFILE", "TEMP", "TMP", "TMPDIR", "PYTHONPATH", "PYTHONIOENCODING",
       "PYTHONUTF8", "SYSTEMROOT", "COMSPEC", "SSH_AUTH_SOCK", "GH_TOKEN", "GITHUB_TOKEN",
       "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "VIRTUAL_ENV", "CI"}
files = [os.path.join(ROOT, "lathe.py"), os.path.join(ROOT, "engine_v2.py")]
files += sorted(glob.glob(os.path.join(INNER, "tools", "*.py")))
code_vars = set()
for f in files:
    if os.path.exists(f):
        code_vars |= set(extract_env_vars(open(f, encoding="utf-8").read()))
ignore = set(ec.IGNORE) | _OS
res = env_drift(sorted(code_vars), sorted(ec.registry_names()), sorted(ignore))
check("LIVE: no undocumented env vars (registry complete)", res['undocumented'] == [],
      "undocumented: %s" % res['undocumented'])
check("registry is non-trivial (>40 vars documented)", len(ec.registry_names()) > 40)

print("\nenv-drift acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
