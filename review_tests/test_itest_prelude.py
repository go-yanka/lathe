"""ACCEPTANCE — #44 (BEHAVIORAL, model-free): the engine auto-prepends `from <module> import *` to the
generated INTEGRATION test, so a GLUE+INTEGRATION plan builds through the VALIDATED path (the validator bans
`import` inside the plan's INTEGRATION).

The prior test passed even on the pre-fix baseline (it never checked the prelude). This one:
  1. AST-extracts the pure `_make_itest_prelude` from engine_v2.py and checks its construction, and
  2. PROVES the prelude is load-bearing: an INTEGRATION that calls a module function with NO import runs GREEN
     when the prelude is prepended, and dies with NameError when it is not.

Run: python review_tests/test_itest_prelude.py     (repo root)
"""
import ast
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine_v2.py")
PY = sys.executable
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


# 1) extract + unit-check the pure prelude builder
_fn = next((n for n in ast.parse(open(ENGINE, encoding="utf-8").read()).body
            if isinstance(n, ast.FunctionDef) and n.name == "_make_itest_prelude"), None)
if _fn is None:
    check("_make_itest_prelude extracted from engine_v2.py", False)
    print("\nitest-prelude (#44) acceptance: FAILED")
    sys.exit(1)
_ns = {}
exec(compile(ast.Module(body=[_fn], type_ignores=[]), ENGINE, "exec"), _ns)
mk = _ns["_make_itest_prelude"]

check("#44 a written module gets a `from <module> import *` prelude", "from game import *" in mk("game", True))
check("#44 an artifact-only build (no module) gets NO prelude", mk("game", False) == "")
check("#44 no module name -> no prelude", mk("", True) == "")

# 2) BEHAVIORAL: the prelude actually makes an import-less INTEGRATION resolve
td = tempfile.mkdtemp(prefix="itest_")
open(os.path.join(td, "game.py"), "w", encoding="utf-8").write("def evaluate(expr):\n    return 2\n")
INTEGRATION = "assert evaluate('1+1') == 2, 'evaluate wrong'\nprint('itest ok')\n"   # NOTE: no import — validator bans it


def run_itest(prelude):
    itp = os.path.join(td, "_itest_run.py")
    open(itp, "w", encoding="utf-8").write(prelude + INTEGRATION)
    r = subprocess.run([PY, itp], cwd=td, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    return r.returncode, (r.stdout + r.stderr)


rc_with, out_with = run_itest(mk("game", True))
check("#44 itest with the prelude runs GREEN (import-less INTEGRATION resolves)", rc_with == 0, out_with[-160:])
rc_without, out_without = run_itest("")   # pre-fix behavior: no prelude
check("#44 itest WITHOUT the prelude dies (NameError) — proves the prelude is load-bearing",
      rc_without != 0 and "NameError" in out_without, out_without[-160:])

import shutil
shutil.rmtree(td, ignore_errors=True)
print("\nitest-prelude (#44) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
