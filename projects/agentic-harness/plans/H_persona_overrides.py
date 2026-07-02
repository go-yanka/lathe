# H_persona_overrides — #43: the persona market is user-steerable. lathe.config.json may declare
#   "personas": {"priority": {"<name>": <weight>}, "mandatory": ["<name>", ...]}
# mandatory personas are injected on EVERY invocation (review auto / planner) regardless of match;
# priority weights rescale the decider's scores (user preference beats raw word-overlap). Pure decision
# here; the spine (lathe.py review auto + planner_prompt) applies it.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "persona_overrides"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "apply_overrides",
     "prompt": ("Write apply_overrides(scored, priority, mandatory, k) -> list of names. scored is a list of "
                "[name, score(number)] pairs from the decider (may be None/empty). priority is a dict name -> "
                "multiplier (number; missing = 1.0; non-dict/None = {}). mandatory is a list of name strings "
                "(non-list/None = []). Steps: (1) adjusted = score * priority.get(name, 1.0) for each scored "
                "pair; drop pairs with adjusted <= 0. (2) rank by adjusted DESCENDING, ties by original order; "
                "take the first k names (k <= 0 -> none from ranking). (3) result = mandatory names first (in "
                "their list order, skipping non-strings/empties), then the ranked names, deduplicated keeping "
                "first occurrence. Mandatory names are included even if unscored or dropped. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert apply_overrides([['a', 2], ['b', 1]], {}, [], 2) == ['a', 'b']",
        "assert apply_overrides([['a', 2], ['b', 1]], {'b': 5}, [], 2) == ['b', 'a']",
        "assert apply_overrides([['a', 2], ['b', 1]], {}, ['sec'], 1) == ['sec', 'a']",
        "assert apply_overrides([['a', 2]], {}, ['a'], 1) == ['a']",
        "assert apply_overrides([['a', 2], ['b', 1]], {'a': 0}, [], 2) == ['b']",
        "assert apply_overrides(None, {}, ['m'], 3) == ['m']",
        "assert apply_overrides([['a', 1]], None, None, 1) == ['a']",
        "assert apply_overrides([['a', 1], ['b', 1]], {}, [], 0) == []",
        "assert apply_overrides([['a', 1], ['b', 1]], {}, [None, '', 'm'], 0) == ['m']",
        "assert apply_overrides([['a', 3], ['b', 2], ['c', 1]], {'c': 10}, [], 2) == ['c', 'a']",
     ]},
]
