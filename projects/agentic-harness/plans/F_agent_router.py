# F_agent_router — pure decider logic for on-demand agent spawning (the "load the program" layer).
# Authored THROUGH the harness (gated+pinned). The spine (`lathe agent`) wires the catalog load + license-gated
# fetch around it. LLM-INDEPENDENT: output is a persona (prompt text) injected into whatever endpoint is configured.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "agent_router"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "expand_words",
     "prompt": ("Write expand_words(s) -> set. Tokenize + normalize for concept matching (D8: exact-token overlap "
                "missed 'authentication'!='auth'). Steps: if s is None or not a str or blank -> return set(). "
                "Lowercase; split on any run of non-alphanumeric characters; drop empties. For EACH token: (1) look "
                "it up in this SYNONYM CANON map (define it inside the function) and if present use the canonical "
                "form: auth/authentication/authorization/authenticate/login/credential/credentials/oauth -> 'auth'; "
                "database/databases/db/sql/sqlite/postgres/mysql/query/queries -> 'database'; kubernetes/k8s -> 'kubernetes'; "
                "performance/perf/latency/speed/slow -> 'performance'; security/vulnerability/vulnerabilities/"
                "exploit/exploits/injection -> 'security'; test/tests/testing/qa/assert/asserts -> 'test'; "
                "frontend/ui/ux -> 'frontend'; api/endpoint/endpoints/rest -> 'api'; error/errors/exception/"
                "exceptions/failure/failures/bug/bugs -> 'error'; concurrency/async/asyncio/thread/threads/race -> "
                "'concurrency'; deploy/deployment/deployments/release/releases -> 'deploy'; doc/docs/document/"
                "documents/documentation -> 'doc'. (2) if NOT in the map, apply a light stem: if len > 4 and it "
                "ends with 'ies' -> replace with 'y'; elif len > 4 and ends with 'ing' -> drop 'ing'; elif len > 3 "
                "and ends with 'ed' -> drop 'ed'; elif len > 3 and ends with 'es' -> drop 'es'; elif len > 3 and "
                "ends with 's' -> drop 's'. Return the set of results. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert expand_words('authentication bug') == {'auth', 'error'}",
        "assert expand_words('login credentials') == {'auth'}",
        "assert expand_words('databases queries') == {'database'}",
        "assert expand_words('k8s deployments') == {'kubernetes', 'deploy'}",
        "assert expand_words('parsing parsed parses') == {'pars', 'parse'} or expand_words('parsing parsed parses') == {'pars'}",
        "assert expand_words('') == set()",
        "assert expand_words(None) == set()",
        "assert 'design' in expand_words('api design') and 'api' in expand_words('api design')",
        "assert expand_words('tests testing qa') == {'test'}",
     ]},
    {"name": "score_match",
     "prompt": ("Write score_match(need, capability) -> int. Return len(expand_words(need) & "
                "expand_words(capability)) — expand_words already exists in this module's namespace; CALL it, do "
                "not redefine it. None/empty inputs give 0 naturally. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert score_match('api design', 'scalable api and design patterns') == 2",
        "assert score_match('x', '') == 0",
        "assert score_match(None, 'y') == 0",
        "assert score_match('Security Auth', 'security review') == 1",
        "assert score_match('authentication bug', 'security auth vulnerabilities exploit input validation') >= 1",
        "assert score_match('login credentials', 'security auth permission checks') >= 1",
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
                "[name, capability] pairs. Score each entry as len(expand_words(goal) & expand_words(capability)) — "
                "expand_words already exists in this module's namespace; CALL it, do not redefine it. Drop any with "
                "score 0. Sort by score DESCENDING, breaking ties by original list order. Return the first k names. "
                "goal None/empty or entries empty -> []. k <= 0 -> []. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert select_agents_for_goal('api design', [['a','api'],['b','design'],['c','api design']], 2) == ['c','a']",
        "assert select_agents_for_goal('backend security', [['x','backend api'],['y','security review'],['z','css']], 3) == ['x','y']",
        "assert select_agents_for_goal('authentication bug', [['sec','security auth vulnerabilities'],['css','styling']], 1) == ['sec']",
        "assert select_agents_for_goal('zzz', [['a','api']], 3) == []",
        "assert select_agents_for_goal('api', [], 3) == []",
        "assert select_agents_for_goal('', [['a','api']], 3) == []",
        "assert select_agents_for_goal('api', [['a','api tools'],['b','api design']], 0) == []",
     ]},
    {"name": "pick_best",
     "prompt": ("Write pick_best(need, entries) -> str. entries is a list of [name, capability] pairs. Score each "
                "entry as len(expand_words(need) & expand_words(capability)) — expand_words already exists in this "
                "module's namespace; CALL it, do not redefine it. Return the name with the highest score; ties -> "
                "the first in list order. If entries is empty or every score is 0, return ''. None-safe. Never "
                "raise." + "\n" + _ONLY),
     "tests": [
        "assert pick_best('api design', [['a','api design tools'],['b','css styling']]) == 'a'",
        "assert pick_best('zzz', [['a','api']]) == ''",
        "assert pick_best('x', []) == ''",
        "assert pick_best('security audit', [['x','frontend css'],['y','security audit checklist']]) == 'y'",
        "assert pick_best('login credentials', [['css','frontend styling'],['sec','security auth permission']]) == 'sec'",
     ]},
    {"name": "spawn_candidates",
     "prompt": ("Write spawn_candidates(names, entries) -> list. The D7 auto-spawn decision: which decider-selected "
                "personas need an on-demand fetch. names is a list of selected persona name strings (may be None). "
                "entries is a list of [name, vendored, license] triples (may be None). Return, PRESERVING the order "
                "of names, every name whose matching entry (same name) has a falsy vendored flag AND a permissive "
                "license — permissive means the license is a string whose lowercased stripped form starts with one "
                "of 'mit', 'apache', 'bsd', 'isc', 'unlicense', 'cc0'. Names with no matching entry, vendored "
                "entries, and non-permissive/None licenses are all EXCLUDED (fail closed). Duplicates in names keep "
                "only the first occurrence. None/empty inputs -> []. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert spawn_candidates(['a','b'], [['a', False, 'MIT'], ['b', True, 'MIT']]) == ['a']",
        "assert spawn_candidates(['x'], [['x', False, 'GPL-3.0']]) == []",
        "assert spawn_candidates(['x'], [['x', False, None]]) == []",
        "assert spawn_candidates(['p','q'], [['q', False, 'Apache-2.0'], ['p', False, 'bsd-3-clause']]) == ['p','q']",
        "assert spawn_candidates(['ghost'], [['a', False, 'MIT']]) == []",
        "assert spawn_candidates(['a','a'], [['a', False, 'MIT']]) == ['a']",
        "assert spawn_candidates(None, [['a', False, 'MIT']]) == []",
        "assert spawn_candidates(['a'], None) == []",
        "assert spawn_candidates([], []) == []",
     ]},
]
