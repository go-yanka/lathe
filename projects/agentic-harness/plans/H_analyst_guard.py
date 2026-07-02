# H_analyst_guard — D5b (review §15): a WELL-FORMED-BUT-WRONG 200 from the analyst endpoint was
# undetectable — the fallback fired only on connection error / non-2xx / empty, so a reachable-but-stale
# proxy answering syntactically-valid junk was accepted as a review verdict. This adds deterministic
# CONTENT validation: a usable review must be non-trivial AND anchored to the review at hand (a severity
# marker or one of the reviewed files' names). Pure decision; hreview wires it into the fallback chain.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "analyst_guard"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "analyst_response_ok",
     "prompt": ("Write analyst_response_ok(txt, markers) -> list [ok(bool), reason(str)]. Deterministic content "
                "validation of an analyst's review response. Rules, in order: if txt is not a str or "
                "len(txt.strip()) < 40 -> [False, 'too short to be a review']. If markers is a non-empty list of "
                "strings: the response must contain AT LEAST ONE marker case-insensitively -> otherwise "
                "[False, 'response mentions neither a severity nor a reviewed file (wrong-200 guard)']. Markers "
                "that are None/empty strings are skipped; if markers is None/empty or all entries are skipped, the "
                "marker check is waived. Passing everything -> [True, 'ok']. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert analyst_response_ok('HIGH | app.py:10 | swallowed exception | raise', ['HIGH','app.py'])[0] is True",
        "assert analyst_response_ok('no issues found in the reviewed files, the module is clean overall', ['no issues'])[0] is True",
        "assert analyst_response_ok('ok', ['HIGH'])[0] is False",
        "assert analyst_response_ok('', ['HIGH'])[0] is False",
        "assert analyst_response_ok(None, ['HIGH'])[0] is False",
        "assert analyst_response_ok('I am a helpful assistant. How can I help you today with your code?', ['CRITICAL','ledger.py'])[0] is False",
        "assert analyst_response_ok('the file LEDGER.PY has a subtle defect in totals accumulation logic', ['ledger.py'])[0] is True",
        "assert analyst_response_ok('x' * 100, [])[0] is True",
        "assert analyst_response_ok('x' * 100, None)[0] is True",
        "assert analyst_response_ok('x' * 100, ['', None])[0] is True",
     ]},
]
