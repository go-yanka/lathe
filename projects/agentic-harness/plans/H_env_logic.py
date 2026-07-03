# H_env_logic — the env-var SURFACE + anti-drift spine (PR#1 CLI-review suggestion #1). The env vars were
# spread across lathe.py/engine_v2.py/tools/* with no single source of truth, so new ones drifted in
# undocumented. These PURE pieces extract the vars the code actually reads and diff them against a registry;
# a gate then FAILS the build if code uses a var the registry (and `lathe env`) doesn't list.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "env_logic"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "extract_env_vars",
     "kinds": ["edge"],
     "prompt": ("Write extract_env_vars(code) -> sorted list of unique env var NAMES the source reads. Use the "
                "re module (import inside). Match all of these access forms and capture the quoted NAME: "
                "os.environ.get('NAME' or \"NAME\"), os.getenv('NAME' or \"NAME\"), and os.environ['NAME' or "
                "\"NAME\"]. A NAME is one or more of [A-Za-z_][A-Za-z0-9_]*. Return the sorted list of unique "
                "names. If code is not a str, return []. Never raise." + "\n" + _ONLY),
     "tests": [
        "s = \"x = os.environ.get('LATHE_STRICT'); y = os.getenv('HARNESS_MODEL'); z = os.environ['LOCAL_OPENAI_URL']\"",
        "assert extract_env_vars(s) == ['HARNESS_MODEL', 'LATHE_STRICT', 'LOCAL_OPENAI_URL']",
        "assert extract_env_vars('os.environ.get(\"A\", \"def\"); os.environ.get(\"A\")') == ['A']",
        "assert extract_env_vars('no env access here') == []",
        "assert extract_env_vars(None) == [] and extract_env_vars('') == []",
        "assert extract_env_vars('os.getenv(\"B\")\\nos.environ[\\'C\\']') == ['B', 'C']",
        "assert extract_env_vars(\"os.environ.get('Z')\") == ['Z']",
        "assert extract_env_vars(\"d = os.environ.get('LATHE_STRICT'); e = os.environ.get('LATHE_STRICT')\") == ['LATHE_STRICT']",
     ]},
    {"name": "env_drift",
     "kinds": ["edge"],
     "prompt": ("Write env_drift(code_vars, registered, ignore) -> dict {'undocumented': [...], 'unused': [...]}. "
                "code_vars = names the code reads; registered = names the registry documents; ignore = names to "
                "skip entirely (OS/internal). Coerce each of the three to a set of the str items in it (a "
                "non-iterable or None -> empty set). undocumented = sorted(code_vars - registered - ignore) "
                "(vars the code uses but the registry omits — this is the drift to FAIL on). unused = "
                "sorted(registered - code_vars - ignore) (documented but not found in code — advisory only). "
                "Return {'undocumented': undocumented, 'unused': unused}. Never raise; on error return "
                "{'undocumented': [], 'unused': []}." + "\n" + _ONLY),
     "tests": [
        "r = env_drift(['A', 'B', 'C'], ['A', 'B'], []); assert r['undocumented'] == ['C'] and r['unused'] == []",
        "r = env_drift(['A'], ['A', 'B'], []); assert r['undocumented'] == [] and r['unused'] == ['B']",
        "r = env_drift(['A', 'PATH'], ['A'], ['PATH']); assert r['undocumented'] == [] and r['unused'] == []",
        "r = env_drift([], [], []); assert r == {'undocumented': [], 'unused': []}",
        "r = env_drift(None, None, None); assert r == {'undocumented': [], 'unused': []}",
        "r = env_drift(['B', 'A', 'A'], ['A'], []); assert r['undocumented'] == ['B']",
        "r = env_drift(['A', 'B', 'C'], ['C', 'B', 'A'], []); assert r['undocumented'] == [] and r['unused'] == []",
     ]},
]

CRITERIA = [
    {"id": "E1", "text": "Extract the env vars the source code actually reads",
     "tests": ["extract_env_vars"]},
    {"id": "E2", "text": "Diff code vars against the registry to surface undocumented (drift) + unused vars",
     "tests": ["env_drift"]},
]
