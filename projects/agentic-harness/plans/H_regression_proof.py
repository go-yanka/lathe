# H_regression_proof — enforcement mechanism #1 (regression-test-must-fail-on-old-code): a bug fix is not
# accepted unless it ships a test that REPRODUCES the bug — i.e. at least one test in the new set FAILS on
# the OLD accepted implementation. Opt-in (LATHE_REGRESSION_PROOF=1, the bug-fix workflow's mode): on a pin
# miss where an old def exists in the built module, the engine runs the NEW tests against the OLD code
# first; if they ALL pass, the plan change proves nothing — REFUSED before any generation. Pure pieces here
# (old-def extraction + the gate decision); the engine wires the sandbox run.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "regression_proof"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "extract_def",
     "prompt": ("Write extract_def(module_src, fn_name) -> str. Extract the complete source of the TOP-LEVEL "
                "function definition named fn_name from the Python module source string module_src, using ast: "
                "parse module_src; find the top-level ast.FunctionDef (or AsyncFunctionDef) whose name == fn_name; "
                "return ast.get_source_segment(module_src, node) (include decorators by starting from the first "
                "decorator's line if the node has any: use ast.get_source_segment on the node which already "
                "excludes decorators — that is acceptable; just return the segment for the def node). Return '' "
                "when module_src is not a str, does not parse, or has no such top-level def. Nested defs and "
                "methods inside classes must NOT match. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert extract_def('def a(x):\\n    return x + 1\\n\\ndef b(y):\\n    return y', 'a') == 'def a(x):\\n    return x + 1'",
        "assert extract_def('def a(x):\\n    return x', 'b') == ''",
        "assert extract_def('class C:\\n    def m(self):\\n        return 1', 'm') == ''",
        "assert extract_def('def outer():\\n    def inner():\\n        return 2\\n    return inner', 'inner') == ''",
        "assert extract_def('not python ((', 'a') == ''",
        "assert extract_def(None, 'a') == ''",
        "assert extract_def('', 'a') == ''",
        "s = extract_def('x = 1\\n\\ndef f(a, b=2):\\n    c = a + b\\n    return c\\n', 'f'); assert s.startswith('def f(a, b=2):') and s.rstrip().endswith('return c')",
     ]},
    {"name": "proof_gate",
     "prompt": ("Write proof_gate(env_value, old_code, old_passes_all) -> list [blocked(bool), reason(str)]. "
                "The regression-proof decision. If env_value is None, not a str, or its stripped lowercased form "
                "is NOT one of '1','true','yes','on' -> [False, 'regression-proof not required'] (opt-in gate). "
                "If old_code is not a non-empty string -> [False, 'no prior implementation - new function'] (the "
                "rule only applies to CHANGED units). Otherwise: if old_passes_all is True -> [True, 'REFUSED: "
                "every new test PASSES on the old implementation - this change ships no test that reproduces the "
                "bug; add a failing-on-old-code test'] (fail closed); if False -> [False, 'proof present: >=1 new "
                "test fails on the old code']. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert proof_gate(None, 'def f(): pass', True) == [False, 'regression-proof not required']",
        "assert proof_gate('0', 'def f(): pass', True) == [False, 'regression-proof not required']",
        "assert proof_gate('1', '', True) == [False, 'no prior implementation - new function']",
        "assert proof_gate('1', None, True) == [False, 'no prior implementation - new function']",
        "assert proof_gate('1', 'def f(): pass', True)[0] is True",
        "assert 'reproduces' in proof_gate('1', 'def f(): pass', True)[1]",
        "assert proof_gate('YES', 'def f(): pass', False) == [False, 'proof present: >=1 new test fails on the old code']",
        "assert proof_gate(' true ', 'def f(): pass', True)[0] is True",
     ]},
]
