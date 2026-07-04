# H_persona_modes — persona redesign STAGE 4 (issue #9): the two selection modes (BR-5). AUTO (default,
# config-driven N, silent) and INTERACTIVE (the system proposes a slate and the user may drop/add before the
# run). Backwards-compatible: no mode set -> 'auto'. The pure pieces resolve the mode and apply the user's
# drop/add over the proposed slate while honouring the always-on mandatory set.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "persona_modes"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "resolve_mode",
     "kinds": ["edge"],
     "prompt": ("Write resolve_mode(interactive, config_mode) -> 'interactive' or 'auto'. If `interactive` is "
                "truthy -> 'interactive'. Else if config_mode is a str whose stripped lowercase form == "
                "'interactive' -> 'interactive'. Otherwise -> 'auto' (the default — backwards-compatible: an "
                "existing deployment with no mode set stays auto). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert resolve_mode(True, None) == 'interactive'",
        "assert resolve_mode(False, 'interactive') == 'interactive'",
        "assert resolve_mode(False, 'INTERACTIVE') == 'interactive'",
        "assert resolve_mode(False, 'auto') == 'auto'",
        "assert resolve_mode(False, None) == 'auto'",
        "assert resolve_mode(0, '') == 'auto'",
     ]},
    {"name": "apply_selection_overrides",
     "kinds": ["edge"],
     "prompt": ("Write apply_selection_overrides(proposed, drop, add, mandatory) -> list. Start from `proposed` "
                "(a list of persona-name strings; non-list -> []). Remove any name in `drop` (iterable of "
                "names). Then append each name in `add` (iterable) that is not already present. Then ensure "
                "every name in `mandatory` (iterable, the always-on set) is present, appending any that are "
                "missing. Throughout: keep only str names, and DEDUPE preserving first-seen order. drop/add/"
                "mandatory that aren't iterable -> treated as empty. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert apply_selection_overrides(['a','b','c'], ['b'], ['d'], []) == ['a','c','d']",
        "assert apply_selection_overrides(['a','b'], [], [], ['sec']) == ['a','b','sec']",
        "assert apply_selection_overrides(['a','b'], ['a','b'], [], ['x']) == ['x']",
        "assert apply_selection_overrides('nope', [], [], []) == []",
        "assert apply_selection_overrides(['a','a','b'], [], [], []) == ['a','b']",
        "assert apply_selection_overrides(['a'], [], ['a','b'], []) == ['a','b']",
        "assert apply_selection_overrides(['a','b'], ['b'], ['b'], []) == ['a','b']",
        "assert apply_selection_overrides(['a','b'], None, None, None) == ['a','b']",
     ]},
]

CRITERIA = [
    {"id": "M1", "text": "Resolve auto vs interactive mode; default auto (backwards-compatible)", "tests": ["resolve_mode"]},
    {"id": "M2", "text": "Apply the user's drop/add over the proposed slate while honouring the mandatory set",
     "tests": ["apply_selection_overrides"]},
]
