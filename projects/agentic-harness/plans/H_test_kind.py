# H_test_kind — enforcement mechanism #5 (required KIND of test per contract): comprehensiveness isn't only
# "how many mutants die" — it's whether the RIGHT SHAPE of test exists. A plan/function may declare
# KIND requirements (e.g. an enhancement must ship a PROPERTY test for each invariant; a parser must ship a
# ROUNDTRIP; a boundary-heavy fn must ship EDGE cases). Under LATHE_TEST_KIND=1 (forced by STRICT), the
# validator/engine refuses a function whose declared kinds aren't all present in its tests. Detection is
# structural + deterministic (no model): kinds are recognized by marker patterns in the test strings.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "test_kind"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "detect_kinds",
     "prompt": ("Write detect_kinds(tests) -> set of kind-name strings present in a list of assert-string tests. "
                "tests None/empty/non-list -> empty set. FIRST strip each test's trailing COMMENT so a trigger "
                "word in a comment can never satisfy a kind (this closes a fail-open): for each test string, scan "
                "its characters tracking whether you are inside a single-quote or double-quote string (a quote "
                "char toggles that quote's state only when the previous char is not a backslash); at the first "
                "'#' seen while NOT inside any quote, cut the rest of that test. This preserves code (brackets, "
                "operators, string contents) but drops comments. Build a lowercased blob = the comment-stripped "
                "tests joined by newlines. Recognize these kinds: "
                "'property' if any (stripped) test contains ('for ' AND ('in range' OR 'in [' OR 'assert all(' OR "
                "'hypothesis')) OR contains 'sorted(' OR 'reversed(' (a quantified/looped/ordering invariant); "
                "'roundtrip' if the blob has any of these pairs both present: ['encode'+'decode', 'dumps'+'loads', "
                "'parse'+'format', 'serialize'+'deserialize', 'to_'+'from_']; "
                "'edge' if blob contains any of ['== 0', '== -', \"'' \", '[]', '{}', 'none', 'empty', ' -1'] "
                "(a zero/empty/negative/None boundary); "
                "'error' if blob contains any of ['raises', 'pytest.raises', 'try:', 'except', 'error', 'invalid']; "
                "'example' if there is at least one plain assert (any stripped test containing 'assert'). Return "
                "the set of kinds found. Never raise. (Define the checks inline; import only re/tokenize if you "
                "want, but a manual char scan for comment stripping is fine.)" + "\n" + _ONLY),
     "tests": [
        "assert 'property' in detect_kinds(['assert all(f(i) >= 0 for i in range(5))'])",
        "assert 'roundtrip' in detect_kinds(['assert decode(encode(x)) == x'])",
        "assert 'edge' in detect_kinds(['assert f([]) == 0'])",
        "assert 'error' in detect_kinds(['try:\\n    f(-1)\\nexcept ValueError:\\n    pass'])",
        "assert 'example' in detect_kinds(['assert f(2) == 4'])",
        "assert detect_kinds([]) == set()",
        "assert detect_kinds(None) == set()",
        "assert 'property' not in detect_kinds(['assert f(2) == 4'])",
        "assert 'roundtrip' in detect_kinds(['assert loads(dumps(d)) == d'])",
        "assert 'error' not in detect_kinds(['assert f(2) == 2  # never raises'])",
        "assert 'error' not in detect_kinds(['assert f(1) == 1  # error case handled'])",
        "assert 'property' in detect_kinds(['assert f([3,1,2]) == sorted([3,1,2])'])",
     ]},
    {"name": "kind_gaps",
     "prompt": ("Write kind_gaps(env_value, required, present) -> list of missing-kind problem strings. If "
                "env_value is None, not a str, or its stripped lowercased form is NOT one of '1','true','yes','on' "
                "-> return [] (opt-in gate off). required is a list of kind-name strings the contract demands "
                "(None/empty -> []); present is a set/list of kinds actually found (None -> empty). For each kind "
                "in required (preserve order, skip non-str/empty, case-insensitive compare) that is NOT in present "
                "-> add the string \"missing required test kind: '<kind>'\". Return the list. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert kind_gaps(None, ['property'], set()) == []",
        "assert kind_gaps('0', ['property'], set()) == []",
        "assert kind_gaps('1', ['property'], set()) == [\"missing required test kind: 'property'\"]",
        "assert kind_gaps('1', ['property'], {'property'}) == []",
        "assert kind_gaps('1', ['property', 'edge'], {'edge'}) == [\"missing required test kind: 'property'\"]",
        "assert kind_gaps('1', ['PROPERTY'], {'property'}) == []",
        "assert kind_gaps('1', None, {'x'}) == []",
        "assert kind_gaps('yes', ['roundtrip'], {'example'}) == [\"missing required test kind: 'roundtrip'\"]",
     ]},
]

CRITERIA = [
    {"id": "K1", "text": "Detect a test's KINDS from its CODE (comments stripped, so a comment can't satisfy a kind)",
     "tests": ["detect_kinds"]},
    {"id": "K2", "text": "Report which required kinds are missing (opt-in gate)",
     "tests": ["kind_gaps"]},
]
