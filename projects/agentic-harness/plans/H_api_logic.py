# H_api_logic — the REST API's security + request-shaping SPINE (PR#1 reviewer proposal; owner: build full v0).
# The HTTP glue lives in lathe_api.py; these PURE, gate-able pieces are the parts that MUST be right: bearer
# extraction, constant-time auth, the env-override ALLOW-LIST (a caller must never set LATHE_TRUST_PLAN/SANDBOX/
# endpoints), plan-XOR-goal validation, and job-response shaping. Built through the harness so they're tested.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "api_logic"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "bearer_token",
     "kinds": ["edge"],
     "prompt": ("Write bearer_token(header) -> str: extract the token from an HTTP Authorization header of the "
                "form 'Bearer <token>'. The word 'bearer' is case-INSENSITIVE and there is exactly one space "
                "before the token; strip surrounding whitespace from the header first. Return the token string, "
                "or '' if header is not a str or does not match. Never raise. Use no imports beyond the standard "
                "str methods (or re, imported inside)." + "\n" + _ONLY),
     "tests": [
        "assert bearer_token('Bearer abc123') == 'abc123'",
        "assert bearer_token('bearer XYZ') == 'XYZ'",
        "assert bearer_token('  Bearer   tok  '.strip()) == 'tok' or bearer_token('Bearer tok') == 'tok'",
        "assert bearer_token('Basic abc') == ''",
        "assert bearer_token('') == '' and bearer_token(None) == ''",
        "assert bearer_token('Bearer ') == ''",
        "assert bearer_token('BEARER t0k3n') == 't0k3n'",
     ]},
    {"name": "auth_ok",
     "kinds": ["edge"],
     "prompt": ("Write auth_ok(header, expected) -> bool: True iff the Authorization `header` carries a bearer "
                "token that equals `expected`, compared in CONSTANT TIME. Import hmac inside and use "
                "hmac.compare_digest. If `expected` is falsy (None or '') or not a str -> return False (a server "
                "with no token configured must refuse everything, fail-closed). Extract the token the same way "
                "bearer_token does (Bearer, case-insensitive) — you may re-implement inline. Never raise; on any "
                "error return False." + "\n" + _ONLY),
     "tests": [
        "assert auth_ok('Bearer secret', 'secret') is True",
        "assert auth_ok('Bearer wrong', 'secret') is False",
        "assert auth_ok('bearer secret', 'secret') is True",
        "assert auth_ok('Bearer secret', '') is False and auth_ok('Bearer secret', None) is False",
        "assert auth_ok('', 'secret') is False and auth_ok(None, 'secret') is False",
        "assert auth_ok('Basic secret', 'secret') is False",
     ]},
    {"name": "env_allowlist",
     "kinds": ["edge"],
     "prompt": ("Write env_allowlist(env, allow) -> dict: return only the entries of `env` whose KEY is in "
                "`allow`, with every value coerced to str. This is a request-override guard — a caller may set "
                "only allow-listed env keys, never trust/sandbox/endpoint vars. If env is not a dict -> return "
                "{}. Coerce `allow` to a set (non-iterable/None -> empty set, so nothing passes). Never raise." + "\n" + _ONLY),
     "tests": [
        "assert env_allowlist({'LATHE_STRICT': '1', 'LATHE_TRUST_PLAN': '1'}, ['LATHE_STRICT']) == {'LATHE_STRICT': '1'}",
        "assert env_allowlist({'LATHE_TRIES': 3}, ['LATHE_TRIES']) == {'LATHE_TRIES': '3'}",
        "assert env_allowlist({'X': '1'}, []) == {} and env_allowlist({'X': '1'}, None) == {}",
        "assert env_allowlist('nope', ['X']) == {}",
        "assert env_allowlist({'A': '1', 'B': '2'}, ['A', 'B', 'C']) == {'A': '1', 'B': '2'}",
        "assert env_allowlist({}, ['A']) == {}",
     ]},
    {"name": "classify_build_body",
     "kinds": ["edge"],
     "prompt": ("Write classify_build_body(body) -> list [ok(bool), kind(str), value(str), error(str)]. A build "
                "request must carry EXACTLY ONE of a non-empty string 'plan' or a non-empty string 'goal'. "
                "Rules: body not a dict -> [False, '', '', 'body must be a JSON object']. Let p = body.get("
                "'plan') if it is a non-empty str else None; g = body.get('goal') if it is a non-empty str else "
                "None. If p and g both set -> [False, '', '', 'provide exactly one of plan or goal, not both']. "
                "If neither -> [False, '', '', 'provide a plan (path) or a goal (string)']. If only p -> [True, "
                "'plan', p, '']. If only g -> [True, 'goal', g, '']. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert classify_build_body({'plan': 'plans/x.py'}) == [True, 'plan', 'plans/x.py', '']",
        "assert classify_build_body({'goal': 'parse a date'}) == [True, 'goal', 'parse a date', '']",
        "r = classify_build_body({'plan': 'x', 'goal': 'y'}); assert r[0] is False and 'both' in r[3]",
        "r = classify_build_body({}); assert r[0] is False and r[1] == '' and r[2] == ''",
        "r = classify_build_body({'plan': ''}); assert r[0] is False",
        "assert classify_build_body('nope')[0] is False",
        "assert classify_build_body({'goal': 'g', 'extra': 1}) == [True, 'goal', 'g', '']",
     ]},
    {"name": "job_view",
     "kinds": ["edge"],
     "prompt": ("Write job_view(job) -> dict: shape a build-job record for the API response. job is a dict with "
                "a 'status' key (one of 'queued','running','done','failed') and an optional 'result'. Return "
                "{'status': job['status'], 'result': job['result']} ONLY when status is 'done' or 'failed' AND "
                "a 'result' key is present; otherwise return {'status': job['status']} (no result key). If job "
                "is not a dict or has no 'status' -> {'status': 'unknown'}. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert job_view({'status': 'queued'}) == {'status': 'queued'}",
        "assert job_view({'status': 'running', 'result': {'x': 1}}) == {'status': 'running'}",
        "assert job_view({'status': 'done', 'result': {'build_ok': True}}) == {'status': 'done', 'result': {'build_ok': True}}",
        "assert job_view({'status': 'failed', 'result': {'build_ok': False}}) == {'status': 'failed', 'result': {'build_ok': False}}",
        "assert job_view({'status': 'done'}) == {'status': 'done'}",
        "assert job_view('nope') == {'status': 'unknown'} and job_view({}) == {'status': 'unknown'}",
     ]},
]

CRITERIA = [
    {"id": "P1", "text": "Extract a bearer token from the Authorization header", "tests": ["bearer_token"]},
    {"id": "P2", "text": "Authenticate in constant time; fail closed when no token is configured", "tests": ["auth_ok"]},
    {"id": "P3", "text": "Restrict caller env overrides to an allow-list (no trust/sandbox/endpoint vars)", "tests": ["env_allowlist"]},
    {"id": "P4", "text": "Validate a build request carries exactly one of plan or goal", "tests": ["classify_build_body"]},
    {"id": "P5", "text": "Shape a job record for the response (result only when terminal)", "tests": ["job_view"]},
]
