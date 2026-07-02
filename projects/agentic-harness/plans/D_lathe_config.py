# D_lathe_config — pure config parse + precedence logic for a single lathe config file (endpoints/models/checkin).
# Authored THROUGH the harness (gated+pinned). The spine loads the file + maps it to env (env overrides config).
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "lathe_config"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "parse_config",
     "prompt": ("Write parse_config(text) that parses a JSON config string into a dict. Use json.loads INSIDE the "
                "function. If the result is a dict, return it; if it parses to anything else (list, number, etc.) "
                "return {}. On any error, or for None/empty input, return {}. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert parse_config('{\"a\": 1}') == {'a': 1}",
        "assert parse_config('') == {}",
        "assert parse_config(None) == {}",
        "assert parse_config('not json') == {}",
        "assert parse_config('[1,2]') == {}",
        "assert parse_config('{\"analyst\": {\"model\": \"sonnet\"}}') == {'analyst': {'model': 'sonnet'}}",
     ]},
    {"name": "pick",
     "prompt": ("Write pick(env_val, cfg_val, default). Precedence: return env_val if it is truthy; else return "
                "cfg_val if it is truthy; else return default. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert pick('e', 'c', 'd') == 'e'",
        "assert pick('', 'c', 'd') == 'c'",
        "assert pick(None, 'c', 'd') == 'c'",
        "assert pick(None, None, 'd') == 'd'",
        "assert pick('', '', 'd') == 'd'",
        "assert pick('a', None, 'd') == 'a'",
     ]},
]
