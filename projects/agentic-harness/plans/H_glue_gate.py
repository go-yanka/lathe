# H_glue_gate — enforcement mechanism #6 (gate the glue): GLUE is the architect's HAND-WRITTEN wiring,
# appended after the gated functions — the most bug-prone part, and today it ships UNVERIFIED unless the
# plan happens to carry an INTEGRATION block. Under STRICT (or LATHE_GATE_GLUE=1), substantive GLUE must be
# exercised by an INTEGRATION test or the module is refused. This is the mechanism that lets the copy finally
# say "nothing ships untested" instead of "no function ships untested". Pure decision; engine wires it in.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "glue_gate"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "count_glue_lines",
     "prompt": ("Write count_glue_lines(glue) -> int counting the SUBSTANTIVE STATEMENTS in the string `glue` "
                "(NOT physical newlines — so statements packed onto one line with ';' cannot slip under the "
                "threshold). Import ast inside. glue None or not a str -> 0. Try ast.parse(glue): on success, "
                "walk the tree and return the count of every node that is an instance of ast.stmt (counts "
                "top-level AND nested statements; comments/blank lines aren't nodes, so they're excluded). If "
                "ast.parse raises SyntaxError, FALL BACK to the physical count: split on newlines, strip each, "
                "count lines that are non-empty and don't start with '#'. Never raise; on any other error -> 0." + "\n" + _ONLY),
     "tests": [
        "assert count_glue_lines('a = 1\\n\\n# comment\\nb = 2') == 2",
        "assert count_glue_lines('   \\n# only comment') == 0",
        "assert count_glue_lines('x=1') == 1",
        "assert count_glue_lines('') == 0",
        "assert count_glue_lines(None) == 0",
        "assert count_glue_lines(42) == 0",
        "assert count_glue_lines('def main():\\n    run()\\n    return 0') == 3",
        "assert count_glue_lines('a=1; b=2; c=3; d=4; e=5') == 5",
        "assert count_glue_lines('a=1; import os; os.system(\\'id\\')') == 3",
        "assert count_glue_lines('a = = =') == 1",
     ]},
    {"name": "glue_gap",
     "prompt": ("Write glue_gap(env_value, glue_lines, has_integration, threshold) -> list [blocked(bool), "
                "reason(str)]. The gate-the-glue decision. If env_value is None, not a str, or its stripped "
                "lowercased form is NOT one of '1','true','yes','on' -> [False, 'glue gate not required'] (opt-in). "
                "If glue_lines is not an int (bools excluded) or glue_lines <= threshold -> [False, 'glue is "
                "trivial - not gated'] (a couple of wiring lines don't need an integration test). If "
                "has_integration is truthy -> [False, 'glue exercised by INTEGRATION']. Otherwise -> [True, "
                "'REFUSED: <glue_lines> lines of hand-written GLUE with no INTEGRATION test - the wiring is "
                "ungated; add an INTEGRATION block that imports the module and asserts its behavior'] with "
                "glue_lines substituted. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert glue_gap(None, 10, False, 2) == [False, 'glue gate not required']",
        "assert glue_gap('0', 10, False, 2) == [False, 'glue gate not required']",
        "assert glue_gap('1', 1, False, 2) == [False, 'glue is trivial - not gated']",
        "assert glue_gap('1', 2, False, 2) == [False, 'glue is trivial - not gated']",
        "assert glue_gap('1', 5, True, 2) == [False, 'glue exercised by INTEGRATION']",
        "assert glue_gap('1', 5, False, 2)[0] is True",
        "assert '5' in glue_gap('1', 5, False, 2)[1] and 'INTEGRATION' in glue_gap('1', 5, False, 2)[1]",
        "assert glue_gap('1', 'x', False, 2) == [False, 'glue is trivial - not gated']",
        "assert glue_gap('1', True, False, 2) == [False, 'glue is trivial - not gated']",
        "assert glue_gap('yes', 3, False, 2)[0] is True",
     ]},
]

CRITERIA = [
    {"id": "G1", "text": "Count substantive glue by STATEMENTS (AST), so ';'-packing can't evade the threshold",
     "tests": ["count_glue_lines"]},
    {"id": "G2", "text": "Refuse substantive glue that has no integration test (opt-in gate)",
     "tests": ["glue_gap"]},
]
