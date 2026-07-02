# H_strict_mode — LATHE_STRICT=1: the SDLC enforcement umbrella (owner directive: the proof discipline is
# not a bug-fix nicety — ALL development, new + enhancement, must be forced through it when following the
# SDLC process). Strict mode composes every enforcement mechanism, no picking and choosing:
#   - LATHE_TEST_ACK=1          (tests are read + acknowledged before they define truth)
#   - LATHE_REGRESSION_PROOF=1  (changed code — fix OR enhancement — ships a test that fails on the old impl)
#   - LATHE_LINT_SPEC=block     (new code ships tests a trivial stub cannot satisfy)
#   - LATHE_MUTATION_SCORE=0.5  (the suite must kill >=50% of deterministic mutants of the accepted code)
#   - CRITERIA required         (every plan declares acceptance criteria -> full requirement→test traceability)
# The POLICY itself is a pinned, tested function (this module); the engine only applies it.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "strict_mode"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "strict_defaults",
     "prompt": ("Write strict_defaults(env_value, existing) -> list. The LATHE_STRICT policy: which enforcement "
                "env vars strict mode turns on. If env_value is None, not a str, or its stripped lowercased form "
                "is NOT one of '1','true','yes','on' -> return [] (strict off). Otherwise return the [key, value] "
                "pairs among [['LATHE_TEST_ACK','1'], ['LATHE_REGRESSION_PROOF','1'], ['LATHE_LINT_SPEC','block'], "
                "['LATHE_MUTATION_SCORE','0.5'], ['LATHE_GATE_GLUE','1'], ['LATHE_TEST_KIND','1']] "
                "for which `existing` (a dict or None) does NOT already carry a non-empty string value for that "
                "key — an explicit user setting always wins over the umbrella. Preserve that exact order. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "assert strict_defaults(None, {}) == []",
        "assert strict_defaults('0', {}) == []",
        "assert strict_defaults('1', {}) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_LINT_SPEC','block'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1']]",
        "assert strict_defaults('1', None) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_LINT_SPEC','block'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1']]",
        "assert strict_defaults('1', {'LATHE_LINT_SPEC': 'warn'}) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1']]",
        "assert strict_defaults('1', {'LATHE_TEST_ACK': ''}) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_LINT_SPEC','block'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1']]",
        "assert strict_defaults(' TRUE ', {'LATHE_TEST_ACK':'1','LATHE_REGRESSION_PROOF':'1','LATHE_LINT_SPEC':'block','LATHE_MUTATION_SCORE':'0.5','LATHE_GATE_GLUE':'1','LATHE_TEST_KIND':'1'}) == []",
     ]},
    {"name": "strict_plan_gaps",
     "prompt": ("Write strict_plan_gaps(env_value, has_functions, criteria, has_artifacts) -> list of problem "
                "strings (empty = plan is strict-compliant). If env_value is None, not a str, or its stripped "
                "lowercased form is NOT one of '1','true','yes','on' -> [] (strict off). Then collect problems: "
                "if has_functions is truthy and criteria is None or an empty list -> add 'strict mode requires "
                "declared CRITERIA (requirement->test traceability) for every FUNCTIONS plan'. If has_artifacts "
                "is truthy and has_functions is falsy -> add 'strict mode cannot gate an ARTIFACTS-only plan "
                "(artifact/glue coverage is not yet enforceable) - build it outside STRICT or add gated "
                "FUNCTIONS'. Return the list. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert strict_plan_gaps(None, True, None, False) == []",
        "assert strict_plan_gaps('1', True, None, False) != []",
        "assert strict_plan_gaps('1', True, [], False) != []",
        "assert 'CRITERIA' in strict_plan_gaps('1', True, None, False)[0]",
        "assert strict_plan_gaps('1', True, [{'id':'AC-1'}], False) == []",
        "assert strict_plan_gaps('1', False, None, False) == []",
        "assert strict_plan_gaps('yes', True, None, False) != []",
        "assert strict_plan_gaps('1', False, None, True) != []",
        "assert 'ARTIFACTS-only' in strict_plan_gaps('1', False, None, True)[0]",
        "assert strict_plan_gaps(None, False, None, True) == []",
        "assert strict_plan_gaps('1', True, [{'id':'A'}], True) == []",
     ]},
]
