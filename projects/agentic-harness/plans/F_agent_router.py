# F_agent_router — pure decider logic for on-demand agent spawning (the "load the program" layer).
# Authored THROUGH the harness (gated+pinned). The spine (`lathe agent`) wires the catalog load + license-gated
# fetch around it. LLM-INDEPENDENT: output is a persona (prompt text) injected into whatever endpoint is configured.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "agent_router"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "score_match",
     "prompt": ("Write score_match(need, capability) -> int. Lowercase both; split each on any non-alphanumeric run "
                "into word sets (drop empties); return the number of shared distinct words. None or empty -> 0. "
                "Never raise." + "\n" + _ONLY),
     "tests": [
        "assert score_match('api design', 'scalable api and design patterns') == 2",
        "assert score_match('x', '') == 0",
        "assert score_match(None, 'y') == 0",
        "assert score_match('Security Auth', 'security review') == 1",
        "assert score_match('a-b c', 'a b') == 2",
     ]},
    {"name": "license_ok",
     "prompt": ("Write license_ok(lic) -> bool. Return True only if lic is a string whose lowercased, stripped form "
                "starts with one of: 'mit', 'apache', 'bsd', 'isc', 'unlicense', 'cc0'. Everything else (GPL, AGPL, "
                "LGPL, unknown, empty, None) -> False. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert license_ok('MIT') is True",
        "assert license_ok('Apache-2.0') is True",
        "assert license_ok('apache 2.0') is True",
        "assert license_ok('BSD-3-Clause') is True",
        "assert license_ok('GPL-3.0') is False",
        "assert license_ok('AGPL-3.0') is False",
        "assert license_ok('') is False",
        "assert license_ok(None) is False",
     ]},
    {"name": "select_agents_for_goal",
     "prompt": ("Write select_agents_for_goal(goal, entries, k) -> list of names. entries is a list of "
                "[name, capability] pairs. Score each capability against goal by shared distinct lowercased words "
                "(split on non-alphanumeric). Drop any with score 0. Sort by score DESCENDING, breaking ties by "
                "original list order. Return the first k names. goal None/empty or entries empty -> []. k <= 0 -> []. "
                "Never raise. (Redefine the word overlap inline; do not import.)" + "\n" + _ONLY),
     "tests": [
        "assert select_agents_for_goal('api design', [['a','api'],['b','design'],['c','api design']], 2) == ['c','a']",
        "assert select_agents_for_goal('backend security', [['x','backend api'],['y','security review'],['z','css']], 3) == ['x','y']",
        "assert select_agents_for_goal('zzz', [['a','api']], 3) == []",
        "assert select_agents_for_goal('api', [], 3) == []",
        "assert select_agents_for_goal('', [['a','api']], 3) == []",
        "assert select_agents_for_goal('api', [['a','api tools'],['b','api design']], 0) == []",
     ]},
    {"name": "pick_best",
     "prompt": ("Write pick_best(need, entries) -> str. entries is a list of [name, capability] pairs. Score each "
                "capability against need with the SAME rule as score_match (shared distinct lowercased words). Return "
                "the name with the highest score; ties -> the first in list order. If entries is empty or every score "
                "is 0, return ''. None-safe. Never raise. (Redefine the word-overlap inline; do not import.)" + "\n" + _ONLY),
     "tests": [
        "assert pick_best('api design', [['a','api design tools'],['b','css styling']]) == 'a'",
        "assert pick_best('zzz', [['a','api']]) == ''",
        "assert pick_best('x', []) == ''",
        "assert pick_best('security audit', [['x','frontend css'],['y','security audit checklist']]) == 'y'",
     ]},
]
