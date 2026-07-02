# H_pin_deps — transitive pin invalidation (round-6 review V3 §3: "make-without-depfiles" hole).
# THE RULE: function B's pin may NOT be reused if B's pinned code references any earlier plan function that
# was freshly REGENERATED this run — B was verified against the OLD dependency, so reuse would be
# stale-but-green even when B's own tests happen to pass. Conservative (may regenerate an unchanged B; never
# keeps a stale one). Deps are derived from the pinned CODE itself, so the .pins.json format is unchanged.
# Pure decision built THROUGH the harness; engine_v2 wires it into the reuse check.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "pin_deps"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "code_refs",
     "prompt": ("Write code_refs(code, names) -> list. Which of `names` (a list of function-name strings) does the "
                "Python source string `code` actually REFERENCE? A name counts only as a whole identifier (use a "
                "regex word-ish boundary: the name preceded and followed by a character that is NOT [A-Za-z0-9_]), "
                "so 'parse' must NOT match inside 'parse_amount' or 'reparse'. Return the matching names preserving "
                "the order of `names`, no duplicates. code or names None/empty -> []. Non-str code -> []. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "assert code_refs('def b(x):\\n    return a(x) + 1', ['a']) == ['a']",
        "assert code_refs('def b(x):\\n    return parse_amount(x)', ['parse']) == []",
        "assert code_refs('def c(x):\\n    return b(a(x))', ['a', 'b']) == ['a', 'b']",
        "assert code_refs('def b(x):\\n    return x', ['a']) == []",
        "assert code_refs('', ['a']) == []",
        "assert code_refs(None, ['a']) == []",
        "assert code_refs('a(1)', None) == []",
        "assert code_refs('total = a(1) + a(2)', ['a']) == ['a']",
        "assert code_refs('x = reparse(1)', ['parse']) == []",
     ]},
    {"name": "pin_stale_by_deps",
     "prompt": ("Write pin_stale_by_deps(code, fresh_names) -> bool. True iff the pinned Python source string "
                "`code` references (whole-identifier match: the candidate name NOT adjacent to [A-Za-z0-9_] on "
                "either side) ANY name in fresh_names — meaning a dependency was regenerated this run, so this pin "
                "was verified against a stale dependency and must NOT be reused. code None/empty/non-str -> False. "
                "fresh_names None/empty -> False. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert pin_stale_by_deps('def b(x):\\n    return a(x)', ['a']) is True",
        "assert pin_stale_by_deps('def b(x):\\n    return parse_amount(x)', ['parse']) is False",
        "assert pin_stale_by_deps('def b(x):\\n    return x + 1', ['a']) is False",
        "assert pin_stale_by_deps('def c(x):\\n    return b(x)', ['a', 'b']) is True",
        "assert pin_stale_by_deps('', ['a']) is False",
        "assert pin_stale_by_deps(None, ['a']) is False",
        "assert pin_stale_by_deps('a(1)', []) is False",
        "assert pin_stale_by_deps('a(1)', None) is False",
     ]},
]
