# H_spine_core — operating contract PHASE 1 (issue #12): the pure DECISION core of the enforcement spine.
# Three deterministic resolutions the spine stamps before any work runs: (1) the thinking dial (casual/
# medium/high) from flag > env > config precedence; (2) dial -> depth env stamps (tries / persona count /
# assumption policy) as a DATA row the code applies; (3) command -> contract lookup (unknown -> TRIVIAL {}).
# The spine ORCHESTRATION (guard, phases, finally-emit) is hand-maintained in lathe.py around these.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "spine_core"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "resolve_thinking",
     "kinds": ["edge"],
     "prompt": ("Write resolve_thinking(flag, env_value, config_value) -> one of 'casual', 'medium', 'high'. "
                "Precedence: flag first, then env_value, then config_value. For each candidate in that "
                "order: if it is a str whose stripped lowercase form is one of ('casual', 'medium', 'high'), "
                "return that normalized form; otherwise try the next. If none is valid, return 'medium' (the "
                "default). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert resolve_thinking('high', None, None) == 'high'",
        "assert resolve_thinking(None, 'casual', 'high') == 'casual'",
        "assert resolve_thinking(None, None, ' HIGH ') == 'high'",
        "assert resolve_thinking(None, None, None) == 'medium'",
        "assert resolve_thinking('turbo', 'nope', '') == 'medium'",
        "assert resolve_thinking('', 'medium', None) == 'medium'",
        "assert resolve_thinking(3, ['x'], {'a': 1}) == 'medium'",
     ]},
    {"name": "depth_env",
     "kinds": ["edge"],
     "prompt": ("Write depth_env(level) -> dict of env stamps for a thinking level. Exact table: "
                "'casual' -> {'LATHE_TRIES': '1', 'LATHE_SELECT_N': '1', 'LATHE_ASSUMPTION_POLICY': 'off'}; "
                "'medium' -> {'LATHE_TRIES': '3', 'LATHE_SELECT_N': '2', 'LATHE_ASSUMPTION_POLICY': 'high'}; "
                "'high' -> {'LATHE_TRIES': '5', 'LATHE_SELECT_N': '4', 'LATHE_ASSUMPTION_POLICY': "
                "'high+med'}. Any other input -> the 'medium' row. Return a NEW dict each call (mutating the "
                "result must not affect later calls). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert depth_env('casual') == {'LATHE_TRIES': '1', 'LATHE_SELECT_N': '1', 'LATHE_ASSUMPTION_POLICY': 'off'}",
        "assert depth_env('medium') == {'LATHE_TRIES': '3', 'LATHE_SELECT_N': '2', 'LATHE_ASSUMPTION_POLICY': 'high'}",
        "assert depth_env('high') == {'LATHE_TRIES': '5', 'LATHE_SELECT_N': '4', 'LATHE_ASSUMPTION_POLICY': 'high+med'}",
        "assert depth_env('bogus') == depth_env('medium')",
        "assert depth_env(None) == depth_env('medium')",
        "d = depth_env('casual'); d['LATHE_TRIES'] = '99'; assert depth_env('casual')['LATHE_TRIES'] == '1'",
     ]},
    {"name": "contract_of",
     "kinds": ["edge"],
     "prompt": ("Write contract_of(cmd, contracts) -> dict, the operating contract for a command. Rules: "
                "contracts not a dict -> {}. cmd not a str -> {}. Look up contracts.get(cmd): if the value "
                "is a dict, return a SHALLOW COPY of it (caller mutation must not corrupt the table); "
                "anything else (missing, None, non-dict) -> {} (TRIVIAL: the spine still runs, phases no-op)."
                " Never raise." + "\n" + _ONLY),
     "tests": [
        "T = {'do': {'workflow': 'build-from-goal', 'gate': 1}, 'status': {}, 'bad': 'nope'}",
        "assert contract_of('do', T) == {'workflow': 'build-from-goal', 'gate': 1}",
        "assert contract_of('status', T) == {}",
        "assert contract_of('unknown', T) == {}",
        "assert contract_of('bad', T) == {}",
        "assert contract_of(None, T) == {} and contract_of('do', None) == {}",
        "c = contract_of('do', T); c['gate'] = 0; assert T['do']['gate'] == 1  # table not corrupted",
     ]},
]

CRITERIA = [
    {"id": "S1", "text": "Thinking dial resolved deterministically with flag>env>config precedence, safe default (#12 spine §4)",
     "tests": ["resolve_thinking"]},
    {"id": "S2", "text": "Dial -> depth stamps as a pure data row (tries / personas / assumption policy) (#12 spine §4)",
     "tests": ["depth_env"]},
    {"id": "S3", "text": "Command -> contract lookup, TRIVIAL fallback, table-corruption-safe (#12 spine §2)",
     "tests": ["contract_of"]},
]
