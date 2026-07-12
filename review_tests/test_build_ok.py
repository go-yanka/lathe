"""ACCEPTANCE — #42 (+ #41) (BEHAVIORAL): the green-build predicate build_ok, exercised directly.

engine_v2.py runs a build at import time (no __main__ guard), so we AST-extract the PURE `_compute_build_ok`
function from its source and call it — a real behavioral test of the shipped logic without a model build.

#42: an integration TIMEOUT is a green build ONLY when the plan opted its itest optional; otherwise a hung
     integration is NOT a silent green.
#41: a build with output (functions OR artifacts) is judged; an artifact-only build can be green; no units is not.

Model-free. Run: python review_tests/test_build_ok.py     (repo root)
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine_v2.py")
fails = []


def check(name, ok, detail=""):
    print("  %-66s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


_fn = next((n for n in ast.parse(open(ENGINE, encoding="utf-8").read()).body
            if isinstance(n, ast.FunctionDef) and n.name == "_compute_build_ok"), None)
if _fn is None:
    check("_compute_build_ok extracted from engine_v2.py", False)
    print("\nbuild-ok (#42) acceptance: FAILED")
    sys.exit(1)
_ns = {}
exec(compile(ast.Module(body=[_fn], type_ignores=[]), ENGINE, "exec"), _ns)


def bok(**kw):
    d = dict(passed=2, n_functions=2, artifacts_passed=0, artifacts_total=0, glue_unverified=False,
             integration="PASS :: itest green", regression="SKIPPED", itest_optional=False)
    d.update(kw)
    return _ns["_compute_build_ok"](**d)


check("baseline (all green) is build_ok", bok() is True)
check("#42 an integration TIMEOUT is NOT green when the itest is not optional",
      bok(integration="TIMEOUT (360s) — itest did not complete") is False)
check("#42 an integration TIMEOUT IS green when the plan declares the itest optional",
      bok(integration="TIMEOUT (360s) — itest did not complete", itest_optional=True) is True)
check("an INTEGRATION FAIL is not green", bok(integration="FAIL\ntraceback...") is False)
check("a failed REGRESSION gate is not green", bok(regression="REGRESSION: some_gate") is False)
check("a REGRESSION TIMEOUT is not green", bok(regression="TIMEOUT (300s)") is False)
check("refused (unverified) GLUE is not green", bok(glue_unverified=True) is False)
check("#41 a build with NO units is not green", bok(passed=0, n_functions=0, artifacts_total=0, artifacts_passed=0) is False)
check("#41 an artifact-only build (no functions) CAN be green",
      bok(passed=0, n_functions=0, artifacts_total=1, artifacts_passed=1) is True)
check("a partial function build (1/2) is not green", bok(passed=1, n_functions=2) is False)

print("\nbuild-ok (#42/#41) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
