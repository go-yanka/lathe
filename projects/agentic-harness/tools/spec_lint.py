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


def _stub_survives(fname, body, tests):
    """True if the trivial stub passes EVERY test — i.e. the tests failed to kill it. SECURITY: the probe runs
    plan-authored test strings, so it goes through the harness SANDBOX (isolated process + timeout + scrubbed
    env, and docker/docker-ssh if configured) — NOT a bare subprocess. fname is validated to a bare identifier
    so it can't smuggle code into the `def` line."""
    if not fname or not _IDENT.match(fname):
        return False
    stub = "def %s(*a, **k):\n    %s\n" % (fname, body)
    try:
        from sandbox import run_unit
        ok, _ = run_unit("", stub, list(tests or []))
        return bool(ok)
    except Exception:
        return False


def lint_function(fname, tests):
    """Return a verdict dict: static gaps + which trivial stubs survived + overall ok."""
    tests = [t for t in (tests or []) if isinstance(t, str)]
    gaps = spec_static_gaps("\n".join(tests))
    survivors = [label for label, body in _STUBS if _stub_survives(fname, body, tests)]
    # BLOCKING = a trivial stub passed ALL tests (definitive: the tests don't pin behavior). static gaps are
    # ADVISORY heuristics that don't apply to every function (a dict-only fn has no meaningful 'zero case').
    return {"function": fname, "static_gaps": gaps, "mutation_survivors": survivors,
            "blocking": bool(survivors), "ok": (not survivors and not gaps)}


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
