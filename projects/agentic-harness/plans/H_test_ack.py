# H_test_ack — gate the analyst's tests (review V4 §3 risk 1: "the tests are the real source code of this
# system, and they are the one artifact with no gate"). Opt-in (LATHE_TEST_ACK=1): the engine refuses to
# build a plan whose test set has not been acknowledged; `lathe ack <plan>` shows the tests and records the
# ack keyed by a DIGEST of (name, tests) pairs — so when the analyst rewrites tests (e.g. in the repair
# loop) the ack goes stale and a human re-reads them. Pure logic here; engine/lathe wire the I/O.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "test_ack"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "tests_digest",
     "prompt": ("Write tests_digest(functions) -> str. functions is a list of dicts each having at least 'name' "
                "(str) and 'tests' (list of str) — ignore any other keys. Build the canonical string: for each "
                "function IN LIST ORDER, append name + chr(0) + each test string joined by chr(1), functions "
                "separated by chr(2). Return the sha256 hexdigest of that string encoded utf-8. Empty/None "
                "functions -> the sha256 hexdigest of the empty string. Entries missing name/tests are treated as "
                "name='' / tests=[]. Never raise." + "\n" + _ONLY),
     "tests": [
        "import hashlib; assert tests_digest([]) == hashlib.sha256(b'').hexdigest()",
        "import hashlib; assert tests_digest(None) == hashlib.sha256(b'').hexdigest()",
        "assert tests_digest([{'name':'a','tests':['t1']}]) == tests_digest([{'name':'a','tests':['t1']}])",
        "assert tests_digest([{'name':'a','tests':['t1']}]) != tests_digest([{'name':'a','tests':['t2']}])",
        "assert tests_digest([{'name':'a','tests':['t1']}]) != tests_digest([{'name':'b','tests':['t1']}])",
        "assert tests_digest([{'name':'a','tests':['t1','t2']}]) != tests_digest([{'name':'a','tests':['t2','t1']}])",
        "assert tests_digest([{'name':'a','tests':['t1'],'prompt':'xxx'}]) == tests_digest([{'name':'a','tests':['t1'],'prompt':'yyy'}])",
        "assert len(tests_digest([{'name':'a','tests':['t1']}])) == 64",
     ]},
    {"name": "ack_ok",
     "prompt": ("Write ack_ok(env_value, acks, plan_name, digest) -> list [ok(bool), reason(str)]. The gate "
                "decision for building a plan. If env_value is None, or not a string, or its stripped lowercased "
                "form is NOT one of '1','true','yes','on' -> return [True, 'test-ack not required'] (the gate is "
                "opt-in). Otherwise the gate is ON: acks is a dict (or None) mapping plan_name -> previously-acked "
                "digest; if acks is a dict and acks.get(plan_name) == digest -> [True, 'tests acknowledged']. "
                "Anything else (no entry, stale digest, acks not a dict) -> [False, 'tests NOT acknowledged - run: "
                "lathe ack <plan>'] (fail closed). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert ack_ok(None, {}, 'p', 'd') == [True, 'test-ack not required']",
        "assert ack_ok('0', {}, 'p', 'd') == [True, 'test-ack not required']",
        "assert ack_ok('1', {'p': 'd'}, 'p', 'd') == [True, 'tests acknowledged']",
        "assert ack_ok('1', {'p': 'OLD'}, 'p', 'd')[0] is False",
        "assert ack_ok('1', {}, 'p', 'd')[0] is False",
        "assert ack_ok('1', None, 'p', 'd')[0] is False",
        "assert ack_ok('TRUE', {'p': 'd'}, 'p', 'd') == [True, 'tests acknowledged']",
        "assert ack_ok(' yes ', {}, 'p', 'd')[0] is False",
        "assert ack_ok([], {'p': 'd'}, 'p', 'd') == [True, 'test-ack not required']",
     ]},
]
