# H_strict_mode — LATHE_STRICT=1: the SDLC enforcement umbrella (owner directive: the proof discipline is
# not a bug-fix nicety — ALL development, new + enhancement, must be forced through it when following the
# SDLC process). Strict mode composes every enforcement mechanism, no picking and choosing:
#   - LATHE_TEST_ACK=1          (tests are read + acknowledged before they define truth)
#   - LATHE_REGRESSION_PROOF=1  (changed code — fix OR enhancement — ships a test that fails on the old impl)
#   - LATHE_LINT_SPEC=block     (new code ships tests a trivial stub cannot satisfy)
#   - LATHE_MUTATION_SCORE=0.5  (the suite must kill >=50% of deterministic mutants of the accepted code)
#   - LATHE_GATE_GLUE=1         (hand-written glue must be exercised by an integration test)
#   - LATHE_TEST_KIND=1         (a function gets the shape of test it declares it needs)
#   - LATHE_ASSUMPTION_GATE=1   (unstated high-materiality assumptions must be surfaced + confirmed pre-build)
#   - CRITERIA required         (every plan declares acceptance criteria -> full requirement→test traceability)
# The POLICY itself is a pinned, tested function (this module); the engine only applies it.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "strict_mode"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
# #12 Phase-2 U2 (reviewer finding, CONFIRMED): strict_defaults FILLS-IF-EMPTY, so a pre-exported weak value
# (LATHE_MUTATION_SCORE=0.01, LATHE_LINT_SPEC=warn) SURVIVES STRICT untouched — a caller could lower every
# threshold below the floor by pre-setting env. strict_clamp is the fix: STRICT clamps, never defers.
FUNCTIONS = [
    {"name": "strict_clamp",
     "kinds": ["edge"],
     "prompt": ("Write strict_clamp(env_value, existing) -> list of [key, value, configured] triples: the env "
                "overrides STRICT must apply so no configured value stays below the STRICT floor. If env_value "
                "is not a str, or its stripped lowercase form is not one of ('1','true','yes','on') -> []. "
                "existing is a dict (None/bad -> treat as {}); configured = existing.get(key) if a str else "
                "None. MODE keys force their strict value whenever configured differs (or is missing): "
                "LATHE_TEST_ACK->'1', LATHE_REGRESSION_PROOF->'1', LATHE_LINT_SPEC->'block', "
                "LATHE_GATE_GLUE->'1', LATHE_TEST_KIND->'1', LATHE_ASSUMPTION_GATE->'1'. NUMERIC floor key "
                "LATHE_MUTATION_SCORE (floor 0.5): parse configured as float; if missing, unparseable, or "
                "< 0.5 -> clamp to '0.5'; if >= 0.5 keep it (emit NO triple). Each emitted triple is "
                "[key, forced_value, configured_or_None] in the key order listed above — the third element "
                "makes every clamped/overridden value LOUD for the report. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert strict_clamp('0', {}) == [] and strict_clamp(None, {}) == []",
        "r = strict_clamp('1', {}); assert ['LATHE_LINT_SPEC', 'block', None] in r and ['LATHE_MUTATION_SCORE', '0.5', None] in r and len(r) == 7",
        "assert ['LATHE_LINT_SPEC', 'block', 'warn'] in strict_clamp('1', {'LATHE_LINT_SPEC': 'warn'})  # U2 kill-shot: pre-set weak mode is FORCED",
        "assert ['LATHE_MUTATION_SCORE', '0.5', '0.01'] in strict_clamp('1', {'LATHE_MUTATION_SCORE': '0.01'})  # U2 kill-shot: sub-floor threshold CLAMPED",
        "assert not any(t[0] == 'LATHE_MUTATION_SCORE' for t in strict_clamp('1', {'LATHE_MUTATION_SCORE': '0.8'}))  # above floor -> untouched",
        "assert ['LATHE_MUTATION_SCORE', '0.5', 'abc'] in strict_clamp('1', {'LATHE_MUTATION_SCORE': 'abc'})  # unparseable -> clamped",
        "full = {'LATHE_TEST_ACK':'1','LATHE_REGRESSION_PROOF':'1','LATHE_LINT_SPEC':'block','LATHE_MUTATION_SCORE':'0.5','LATHE_GATE_GLUE':'1','LATHE_TEST_KIND':'1','LATHE_ASSUMPTION_GATE':'1'}",
        "assert strict_clamp(' TRUE ', full) == []  # already strict -> nothing to force",
        "assert strict_clamp('1', None)[0][0] == 'LATHE_TEST_ACK'  # key order stable, None existing tolerated",
     ]},
    {"name": "strict_defaults",
     "prompt": ("Write strict_defaults(env_value, existing) -> list. The LATHE_STRICT policy: which enforcement "
                "env vars strict mode turns on. If env_value is None, not a str, or its stripped lowercased form "
                "is NOT one of '1','true','yes','on' -> return [] (strict off). Otherwise return the [key, value] "
                "pairs among [['LATHE_TEST_ACK','1'], ['LATHE_REGRESSION_PROOF','1'], ['LATHE_LINT_SPEC','block'], "
                "['LATHE_MUTATION_SCORE','0.5'], ['LATHE_GATE_GLUE','1'], ['LATHE_TEST_KIND','1'], "
                "['LATHE_ASSUMPTION_GATE','1']] "
                "for which `existing` (a dict or None) does NOT already carry a non-empty string value for that "
                "key — an explicit user setting always wins over the umbrella. Preserve that exact order. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "assert strict_defaults(None, {}) == []",
        "assert strict_defaults('0', {}) == []",
        "assert strict_defaults('1', {}) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_LINT_SPEC','block'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1'],['LATHE_ASSUMPTION_GATE','1']]",
        "assert strict_defaults('1', None) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_LINT_SPEC','block'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1'],['LATHE_ASSUMPTION_GATE','1']]",
        "assert strict_defaults('1', {'LATHE_LINT_SPEC': 'warn'}) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1'],['LATHE_ASSUMPTION_GATE','1']]",
        "assert strict_defaults('1', {'LATHE_TEST_ACK': ''}) == [['LATHE_TEST_ACK','1'],['LATHE_REGRESSION_PROOF','1'],['LATHE_LINT_SPEC','block'],['LATHE_MUTATION_SCORE','0.5'],['LATHE_GATE_GLUE','1'],['LATHE_TEST_KIND','1'],['LATHE_ASSUMPTION_GATE','1']]",
        "assert strict_defaults(' TRUE ', {'LATHE_TEST_ACK':'1','LATHE_REGRESSION_PROOF':'1','LATHE_LINT_SPEC':'block','LATHE_MUTATION_SCORE':'0.5','LATHE_GATE_GLUE':'1','LATHE_TEST_KIND':'1','LATHE_ASSUMPTION_GATE':'1'}) == []",
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

# Requirement -> test traceability (consumed by `lathe trace`, enforced under LATHE_STRICT).
CRITERIA = [
    {"id": "S1", "text": "strict_defaults fills unset enforcement vars (LEGACY fill-if-empty — superseded for STRICT floors by S3)",
     "tests": ["strict_defaults"]},
    {"id": "S2", "text": "STRICT refuses a plan missing CRITERIA, and refuses an ARTIFACTS-only plan",
     "tests": ["strict_plan_gaps"]},
    {"id": "S3", "text": "STRICT CLAMPS: no pre-set env value may keep a gate below the STRICT floor; every override is loud (#12 U2)",
     "tests": ["strict_clamp"]},
]
