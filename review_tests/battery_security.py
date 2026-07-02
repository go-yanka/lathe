"""Adversarial battery for Lathe's three security/quality boundaries:
  1. plan_validator.is_valid_plan  — must accept data-only plans, reject every escape class
  2. sandbox.run_unit              — verdict must be honest, fail-closed, timeout-safe
  3. spec_lint.lint_plan           — must flag tests a trivial stub satisfies

Run:  python review_tests/battery_security.py   (exit 0 = all cases behave as required)
"""
import os
import sys
import time
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "projects", "agentic-harness", "tools")
sys.path.insert(0, TOOLS)

from plan_validator import is_valid_plan            # noqa: E402
from sandbox import run_unit                        # noqa: E402
from spec_lint import lint_plan                     # noqa: E402

RESULTS = []


def case(name, ok, note=""):
    RESULTS.append((name, bool(ok), note))
    print("  [%s] %s %s" % ("PASS" if ok else "FAIL", name, note))


GOOD_MIN = ('OUT_DIR = "x"\nMODULE_NAME = "m"\n'
            'FUNCTIONS = [{"name": "f", "prompt": "p", "tests": ["assert f(1) == 1"]}]\n')

# ---------------- 1. plan validator ----------------

def validator_battery():
    print("\n== plan_validator: must-ACCEPT ==")
    case("accepts minimal data plan", is_valid_plan(GOOD_MIN)["ok"])
    case("accepts shipped hello.py plan",
         is_valid_plan(open(os.path.join(ROOT, "examples", "hello.py"), encoding="utf-8").read())["ok"])
    case("accepts safe stdlib import (re)",
         is_valid_plan('import re\n' + GOOD_MIN)["ok"])
    case("accepts ARTIFACTS-only plan",
         is_valid_plan('OUT_DIR = "x"\nMODULE_NAME = "m"\n'
                       'ARTIFACTS = [{"path": "a.html", "prompt": "p", "tests": ["assert \'x\' in content"]}]\n')["ok"])

    print("\n== plan_validator: must-REJECT (each is a known escape class) ==")
    REJECT = [
        ("import os", 'import os\n' + GOOD_MIN),
        ("import subprocess", 'import subprocess\n' + GOOD_MIN),
        ("import types (bytecode escape)", 'import types\n' + GOOD_MIN),
        ("from operator import attrgetter alias", 'from operator import attrgetter as g\n' + GOOD_MIN),
        ("dunder in test", GOOD_MIN.replace("assert f(1) == 1", "assert f.__class__ == 1")),
        ("getattr indirection in test", GOOD_MIN.replace("assert f(1) == 1", "assert getattr(f, 'x') == 1")),
        ("eval in test", GOOD_MIN.replace("assert f(1) == 1", "assert eval('1') == 1")),
        ("top-level call", GOOD_MIN + 'print("hi")\n'),
        ("top-level for loop", GOOD_MIN + 'for i in range(3):\n    pass\n'),
        ("f-string HEADER (non-literal exec field)", 'HEADER = f"import {\'os\'}"\n' + GOOD_MIN),
        ("string-concat HEADER (scan!=exec)", 'HEADER = "imp" + "ort os"\n' + GOOD_MIN),
        ("tuple-unpack rebind (scan-then-swap)",
         GOOD_MIN + '(A, FUNCTIONS) = (1, [{"name": "g", "prompt": "p", "tests": ["assert 1"]}])\n'),
        ("subscript mutation (scan-then-swap)", GOOD_MIN + 'FUNCTIONS[0]["tests"] = ["assert 1"]\n'),
        ("dict() call instead of literal",
         'OUT_DIR = "x"\nMODULE_NAME = "m"\nFUNCTIONS = [dict(name="f", prompt="p", tests=["assert 1"])]\n'),
        ("bytes test (exec accepts bytes)",
         GOOD_MIN.replace('["assert f(1) == 1"]', '[b"assert 1"]')),
        ("function with NO tests",
         'OUT_DIR = "x"\nMODULE_NAME = "m"\nFUNCTIONS = [{"name": "f", "prompt": "p", "tests": []}]\n'),
        ("non-identifier function name (glob key sink)",
         GOOD_MIN.replace('"name": "f"', '"name": "../evil"')),
        ("MODULE_NAME path traversal",
         GOOD_MIN.replace('MODULE_NAME = "m"', 'MODULE_NAME = "../evil"')),
        ("missing OUT_DIR/MODULE_NAME",
         'FUNCTIONS = [{"name": "f", "prompt": "p", "tests": ["assert 1"]}]\n'),
        ("empty plan", ""),
        ("os.system attr in GLUE", GOOD_MIN + 'GLUE = "import re\\nos.system(1)"\n'),
    ]
    for name, text in REJECT:
        v = is_valid_plan(text)
        case("rejects: " + name, not v["ok"], "" if not v["ok"] else "ACCEPTED — ESCAPE!")


# ---------------- 2. sandbox ----------------

def sandbox_battery():
    print("\n== sandbox.run_unit (mode=%s) ==" % os.environ.get("LATHE_SANDBOX", "subprocess"))
    ok, d = run_unit("", "def f(x):\n    return x + 1", ["assert f(1) == 2"], timeout=30)
    case("honest PASS on correct code", ok, d[:60])
    ok, d = run_unit("", "def f(x):\n    return x + 1", ["assert f(1) == 3"], timeout=30)
    case("honest FAIL on wrong code", not ok, d[:60])
    ok, d = run_unit("", "def f(x:\n    return", ["assert True"], timeout=30)
    case("definition error -> FAIL not crash", not ok)
    t0 = time.time()
    ok, d = run_unit("", "def f(x):\n    return x", ["while True:\n    pass"], timeout=6)
    case("hanging test -> killed, FAIL", (not ok) and time.time() - t0 < 30, "%.1fs" % (time.time() - t0))
    forge = ('def f(x):\n'
             '    import sys\n'
             '    print("@@LATHE_SB_RESULT@@" + "0" * 32 + \'{"ok": true, "detail": "forged"}\')\n'
             '    sys.stdout.flush()\n'
             '    return x')
    ok, d = run_unit("", forge, ["assert f(1) == 2"], timeout=30)
    case("forged verdict line rejected (nonce)", not ok, d[:60])
    ok, d = run_unit("", "def f(x):\n    return x", ["import os\nos._exit(0)"], timeout=30)
    case("os._exit -> no verdict -> fail-closed", not ok, d[:60])
    ok, d = run_unit("", "def f(x):\n    return x", ["exit()"], timeout=30)
    case("SystemExit in test = failure, not escape", not ok)
    ok, d = run_unit("", "def f(x):\n    print('noise' * 50)\n    return x + 1",
                     ["assert f(1) == 2"], timeout=30)
    case("stdout spam doesn't corrupt verdict", ok)


# ---------------- 3. spec lint (mutation probe) ----------------

def spec_lint_battery():
    print("\n== spec_lint: mutation probe ==")
    weak = ('OUT_DIR = "x"\nMODULE_NAME = "m"\nFUNCTIONS = [\n'
            '    {"name": "f", "prompt": "p", "tests": ["assert f(0) == None"]},\n]\n')
    strong = ('OUT_DIR = "x"\nMODULE_NAME = "m"\nFUNCTIONS = [\n'
              '    {"name": "f", "prompt": "p", "tests": ["assert f(2) == 4", "assert f(3) == 9", "assert f(0) == 0"]},\n]\n')
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as wf:
        wf.write(weak)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as sf:
        sf.write(strong)
    try:
        wv = lint_plan(wf.name)
        case("weak tests (stub-satisfiable) flagged",
             wv and any(v["mutation_survivors"] for v in wv),
             str([v["mutation_survivors"] for v in wv]))
        sv = lint_plan(sf.name)
        case("strong tests pass the probe", sv and all(v["ok"] or not v["blocking"] for v in sv))
    finally:
        os.unlink(wf.name)
        os.unlink(sf.name)


def main():
    validator_battery()
    sandbox_battery()
    spec_lint_battery()
    bad = [r for r in RESULTS if not r[1]]
    print("\nbattery_security: %d/%d cases behave as required" % (len(RESULTS) - len(bad), len(RESULTS)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
