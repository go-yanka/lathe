"""spec_lint — TEST-QUALITY linter (the deepest gap: the engine checks a spec's tests PASS, never that they're
GOOD). A shallow test (e.g. only `assert f(1)==1`) lets the local model generate confidently-WRONG code that
still goes green and ships. spec_lint scores the analyst's tests BEFORE the implementer loops:

  - STATIC gaps (spec_static_gaps, harness-built): missing None/empty/zero cases, too few assertions.
  - MUTATION PROBE (the strong signal): run trivial STUB implementations (return None / 0 / '' / identity / ...)
    against the spec's own tests. If ANY trivial stub passes ALL the tests, the tests do not pin behavior — a
    constant or identity would satisfy them — so the spec is inadequate and must be strengthened.

  lathe lint-spec <plan.py>                 # report per function
  LATHE_LINT_SPEC=warn|block  -> engine runs it as a pre-implementer gate (warn, or refuse to build)

Note: the probe runs stub+tests in a subprocess with a timeout. For UNTRUSTED plans, run under the docker
sandbox (Phase 2). For our own validated plans (tests are literal asserts) a bounded subprocess is fine.
"""
import ast
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    from spec_static_gaps import spec_static_gaps           # harness-built pure static scorer
except Exception:
    def spec_static_gaps(t):
        return []
try:
    import gate_tristate as _TRISTATE                        # #12 U1: pinned tri-state decision core
except Exception:
    _TRISTATE = None

# trivial implementations a GOOD test suite must kill. (label, body)
_STUBS = [
    ("returns None", "return None"),
    ("returns 0", "return 0"),
    ("returns ''", "return ''"),
    ("returns []", "return []"),
    ("returns {}", "return {}"),
    ("returns True", "return True"),
    ("returns False", "return False"),
    ("returns the first positional arg", "return a[0] if a else None"),
]


_IDENT = re.compile(r"[A-Za-z_]\w*\Z")


def _stub_result(fname, body, tests):
    """Tri-state (#12 U1): 'survived' (stub passed ALL tests — tests too weak), 'killed' (a test failed it —
    good), or 'inoperative' (the probe itself could not run — sandbox import/timeout/OOM). The old code did
    `except: return False`, i.e. an unrunnable probe read as 'killed' -> the gate PASSED a spec it never
    actually checked. INOPERATIVE is now surfaced so a STRICT build refuses instead of shipping blind."""
    if not fname or not _IDENT.match(fname):
        return 'inoperative'
    stub = "def %s(*a, **k):\n    %s\n" % (fname, body)
    try:
        from sandbox import run_unit
        ok, _ = run_unit("", stub, list(tests or []))
        return 'survived' if ok else 'killed'
    except Exception:
        return 'inoperative'


def _sandbox_canary():
    """U1 canary pair: prove the probe MECHANISM works before trusting any 'killed' result. A trivially true
    assert MUST pass (positive control) and a trivially false assert MUST be caught (negative control). If the
    sandbox is broken, both come back wrong and the whole lint is declared inoperative rather than green."""
    if _TRISTATE is None:
        return True                       # decision module absent -> legacy behavior (don't newly block)
    try:
        from sandbox import run_unit
        pos, _ = run_unit("", "def _c():\n    return 1\n", ["assert True"])
        neg, _ = run_unit("", "def _c():\n    return 1\n", ["assert False"])
        return _TRISTATE.canary_trustworthy(bool(pos), bool(neg))
    except Exception:
        return False


def lint_function(fname, tests):
    """Return a verdict dict: static gaps + which trivial stubs survived + tri-state verdict + overall ok.
    verdict (#12 U1): 'fail' (a stub survived), 'inoperative' (probe couldn't run / canary miscalibrated),
    else 'pass'. The engine maps verdict->block via gate_tristate.gate_blocks (INOPERATIVE blocks under
    STRICT only — owner's STRICT-first rollout)."""
    tests = [t for t in (tests or []) if isinstance(t, str)]
    gaps = spec_static_gaps("\n".join(tests))
    trustworthy = _sandbox_canary()
    survivors, inoperative = [], (not trustworthy)
    for label, body in _STUBS:
        r = _stub_result(fname, body, tests)
        if r == 'survived':
            survivors.append(label)
        elif r == 'inoperative':
            inoperative = True
    # verdict: a surviving stub is a definitive FAIL; a probe that couldn't run is INOPERATIVE (not a pass);
    # static gaps stay ADVISORY (not every function has a meaningful zero/None case).
    verdict = 'fail' if survivors else ('inoperative' if inoperative else 'pass')
    return {"function": fname, "static_gaps": gaps, "mutation_survivors": survivors,
            "verdict": verdict, "inoperative": inoperative,
            "blocking": bool(survivors), "ok": (verdict == 'pass' and not gaps)}


def _stub_survives(fname, body, tests):        # back-compat shim: old bool API (True == survived)
    return _stub_result(fname, body, tests) == 'survived'


def _extract_functions(plan_src):
    """Pull [{name, tests}] from a plan's FUNCTIONS literal by AST (never exec the plan). Tolerates a non-literal
    'prompt' (implicit concat / + _ONLY) — only 'name' (str literal) and 'tests' (list of str literals) are read."""
    tree = ast.parse(plan_src)
    out = []
    for node in tree.body:                    # MODULE-LEVEL only (not ast.walk — a FUNCTIONS bound inside a def/class/if is not the plan constant)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "FUNCTIONS" for t in node.targets):
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                continue
            for elt in node.value.elts:
                if not isinstance(elt, ast.Dict):
                    continue
                name, tests = None, []
                for k, v in zip(elt.keys, elt.values):
                    key = k.value if isinstance(k, ast.Constant) else None
                    if key == "name" and isinstance(v, ast.Constant):
                        name = v.value
                    elif key == "tests" and isinstance(v, (ast.List, ast.Tuple)):
                        tests = [e.value for e in v.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if name:
                    out.append({"name": name, "tests": tests})
    return out


def lint_plan(plan_path):
    """Lint every function in a plan file. Returns a list of per-function verdicts."""
    with open(plan_path, encoding="utf-8") as f:
        src = f.read()
    return [lint_function(fn["name"], fn["tests"]) for fn in _extract_functions(src)]
