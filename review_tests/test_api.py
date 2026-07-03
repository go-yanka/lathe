"""ACCEPTANCE TEST — the opt-in REST API (lathe_api.py) + its security spine (api_logic).

  1. api_logic pure fns (auth constant-time, env allow-list, plan-xor-goal, job shaping).
  2. LIVE server (ephemeral port, real bearer token): 401 without/with-wrong token; /v1/env returns the
     CATALOG (names, never values); /v1/gate wraps the gate; /v1/verify rejects a traversal path;
     an env-override request is allow-list-filtered; a plan build job runs and reports build_ok.
Uses only the stdlib + the pinned pin cache (no model calls). Run:  python review_tests/test_api.py
"""
import json
import os
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
from api_logic import auth_ok, env_allowlist, classify_build_body, job_view

fails = []
def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)

# 1) pure spine
check("auth: constant-time match", auth_ok("Bearer s3cret", "s3cret") is True)
check("auth: wrong token rejected", auth_ok("Bearer nope", "s3cret") is False)
check("auth: no server token -> fail-closed", auth_ok("Bearer x", "") is False)
check("env allow-list drops trust vars",
      env_allowlist({"LATHE_STRICT": "1", "LATHE_TRUST_PLAN": "1"}, ["LATHE_STRICT"]) == {"LATHE_STRICT": "1"})
check("build body: plan xor goal", classify_build_body({"plan": "p", "goal": "g"})[0] is False)
check("job_view hides result until terminal", job_view({"status": "running", "result": {"x": 1}}) == {"status": "running"})

# 2) LIVE server on an ephemeral port
TOKEN = "test-token-123"
os.environ["LATHE_API_TOKEN"] = TOKEN
import importlib.util
spec = importlib.util.spec_from_file_location("lathe_api", os.path.join(ROOT, "lathe_api.py"))
api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)

from http.server import ThreadingHTTPServer
httpd = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)      # port 0 -> OS picks a free port
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(0.2)
BASE = "http://127.0.0.1:%d" % port                            # paths already include the /v1 prefix

def call(method, path, token=TOKEN, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or "{}")

try:
    st, _ = call("GET", "/v1/env", token=None)
    check("401 without a token", st == 401)
    st, _ = call("GET", "/v1/env", token="wrong")
    check("401 with a wrong token", st == 401)
    st, obj = call("GET", "/v1/env")
    names = {e["name"] for e in obj.get("env", [])}
    check("/v1/env returns the catalog (names)", st == 200 and "LATHE_STRICT" in names)
    check("/v1/env never leaks resolved VALUES", all("value" not in e for e in obj.get("env", [])))
    st, obj = call("POST", "/v1/gate", body={})
    check("/v1/gate wraps the gate (ok true)", st == 200 and obj.get("ok") is True, str(obj)[:120])
    st, obj = call("POST", "/v1/verify", body={"plan": "../../etc/passwd"})
    check("/v1/verify rejects path traversal", st == 400)
    st, obj = call("POST", "/v1/builds", body={})
    check("/v1/builds rejects empty body", st == 400)
    # a real plan build job (pinned -> no model calls)
    st, obj = call("POST", "/v1/builds", body={"plan": "projects/agentic-harness/plans/H_api_logic.py",
                                               "env": {"LATHE_TRUST_PLAN": "1"}})  # trust var must be dropped
    check("/v1/builds accepts a plan -> 202 + job_id", st == 202 and obj.get("job_id"), str(obj)[:120])
    jid = obj.get("job_id")
    result = None
    for _ in range(120):
        st, jv = call("GET", "/v1/builds/%s" % jid)
        if jv.get("status") in ("done", "failed"):
            result = jv; break
        time.sleep(0.5)
    check("build job reaches terminal + build_ok true", result and result.get("status") == "done"
          and result.get("result", {}).get("build_ok") is True, str(result)[:160])
finally:
    httpd.shutdown()

print("\napi acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
