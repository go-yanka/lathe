"""lathe_api.py — an opt-in local HTTP/REST surface for Lathe (PR#1 reviewer proposal; owner: full v0).

For NON-agent consumers (a web dashboard, language-agnostic services, CI-over-HTTP). Agents already have MCP.
Design (see docs/API_PROPOSAL_REST.md): wrap the SAME engine path (reuse `lathe build --json`), refuse by
default (mcp_safe.reject_flags/is_within_root), local-bind + bearer-token auth (constant-time), builds are
async jobs. No gate is weakened — the API is just another caller of the gated engine.

Start it:  LATHE_API_TOKEN=... python lathe_api.py            (127.0.0.1:8799)
           lathe serve                                          (same, via the CLI)

Security invariants:
  * refuses to start with no LATHE_API_TOKEN (fail-closed).
  * binds 127.0.0.1 unless --bind 0.0.0.0 AND LATHE_SANDBOX=docker/docker-ssh (never run remote plans in-proc).
  * every path -> is_within_root; every free string -> reject_flags; caller env overrides -> api_logic allow-list.
  * GET /v1/env returns the catalog (names/roles/defaults), NEVER resolved values.
"""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
sys.path.insert(0, os.path.join(ROOT, "projects", "agentic-harness", "tools"))
from api_logic import auth_ok, env_allowlist, classify_build_body, job_view   # harness-built, pinned
from mcp_safe import reject_flags, is_within_root                              # harness-built input guards

# caller may override ONLY these (never trust/sandbox/endpoint vars) — the request env allow-list.
_ENV_ALLOW = {"LATHE_STRICT", "LATHE_ASSUMPTION_POLICY", "LATHE_TEST_KIND", "LATHE_MUTATION_SCORE",
              "LATHE_REGRESSION_PROOF", "LATHE_GATE_GLUE", "LATHE_TEST_ACK", "LATHE_TRIES"}

_JOBS = {}                          # job_id -> {"status":..., "result":...}
_JOBS_LOCK = threading.Lock()
_JOB_SEQ = [0]


def _run_json(argv, extra_env=None):
    """Run a lathe CLI subprocess, return (rc, stdout)."""
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    r = subprocess.run([PY, os.path.join(ROOT, "lathe.py")] + argv, cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=int(os.environ.get("LATHE_RUN_TIMEOUT", "0")) or None, env=env)
    return r.returncode, (r.stdout or "")


def _catalog():
    import importlib.util
    spec = importlib.util.spec_from_file_location("env_catalog", os.path.join(ROOT, "env_catalog.py"))
    ec = importlib.util.module_from_spec(spec); spec.loader.exec_module(ec)
    return [{"name": n, "group": g, "role": r, "default": d} for (n, g, r, d) in ec.REGISTRY]


def _build_job(job_id, kind, value, extra_env):
    with _JOBS_LOCK:
        _JOBS[job_id]["status"] = "running"
    try:
        if kind == "plan":
            rc, out = _run_json(["build", value, "--json"], extra_env)
            import re
            m = re.search(r"(\{.*\"build_ok\".*\})", out, re.S)
            result = json.loads(m.group(1)) if m else {"build_ok": False, "error": "no metrics", "rc": rc}
        else:                                                   # goal -> `do` (autonomy path)
            rc, out = _run_json(["do", value], extra_env)
            import re
            m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", out, re.S)
            result = json.loads(m.group(1)) if m else {"build_ok": rc == 0, "output": out[-2000:]}
        status = "done" if result.get("build_ok") else "failed"
    except Exception as e:
        result, status = {"build_ok": False, "error": str(e)}, "failed"
    with _JOBS_LOCK:
        _JOBS[job_id] = {"status": status, "result": result}


class Handler(BaseHTTPRequestHandler):
    server_version = "lathe-api/0"

    def log_message(self, *a):                                  # quiet by default
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self):
        if not auth_ok(self.headers.get("Authorization", ""), os.environ.get("LATHE_API_TOKEN", "")):
            self._send(401, {"error": "unauthorized: missing/invalid bearer token"}); return False
        return True

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", "0") or "0")
            return json.loads(self.rfile.read(n) or "{}") if n else {}
        except Exception:
            return None

    # ---- read-only (sync) ----
    def do_GET(self):
        if not self._authed():
            return
        p = self.path.split("?", 1)[0].rstrip("/")
        if p == "/v1/env":
            return self._send(200, {"env": _catalog()})        # catalog only — NEVER resolved values
        if p == "/v1/plans":
            rc, out = _run_json(["plans"]); return self._send(200, {"plans": out.strip().splitlines()})
        if p == "/v1/metrics":
            rc, out = _run_json(["metrics", "summary"]); return self._send(200, {"metrics": out})
        if p.startswith("/v1/builds/"):
            jid = p.rsplit("/", 1)[-1]
            with _JOBS_LOCK:
                job = _JOBS.get(jid)
            return self._send(200 if job else 404, job_view(job) if job else {"error": "no such job"})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._authed():
            return
        p = self.path.split("?", 1)[0].rstrip("/")
        body = self._body()
        if body is None:
            return self._send(400, {"error": "invalid JSON body"})

        if p == "/v1/gate":
            rc, out = _run_json(["gate"]); return self._send(200, {"ok": rc == 0, "report": out})

        if p in ("/v1/verify", "/v1/trace"):
            plan = body.get("plan", "")
            if not isinstance(plan, str) or plan.startswith("-") or not is_within_root(ROOT, plan):
                return self._send(400, {"error": "'plan' must be a path inside the project (no '-', no '..')"})
            rc, out = _run_json([p.rsplit("/", 1)[-1], plan]); return self._send(200, {"ok": rc == 0, "output": out})

        if p == "/v1/review":
            ok_l, lenses = reject_flags(body.get("lenses", ""))
            ok_f, files = reject_flags(" ".join(body.get("files", [])) if isinstance(body.get("files"), list) else body.get("files", ""))
            if not (ok_l and ok_f):
                return self._send(400, {"error": "arguments must not start with '-' (injection guard)"})
            if not files or not all(is_within_root(ROOT, f) for f in files):
                return self._send(400, {"error": "'files' must be paths inside the project"})
            rc, out = _run_json(["review"] + lenses + files); return self._send(200, {"ok": rc == 0, "output": out})

        if p == "/v1/builds":                                   # async job
            ok, kind, value, err = classify_build_body(body)
            if not ok:
                return self._send(400, {"error": err})
            if kind == "plan" and (value.startswith("-") or not is_within_root(ROOT, value)):
                return self._send(400, {"error": "'plan' must be a path inside the project"})
            okg, goal_tokens = (True, [value]) if kind == "plan" else reject_flags(value)
            if not okg:
                return self._send(400, {"error": "'goal' must not start with '-'"})
            extra_env = env_allowlist(body.get("env", {}), _ENV_ALLOW)
            with _JOBS_LOCK:
                _JOB_SEQ[0] += 1
                jid = "job_%d" % _JOB_SEQ[0]
                _JOBS[jid] = {"status": "queued"}
            threading.Thread(target=_build_job, args=(jid, kind, value, extra_env), daemon=True).start()
            return self._send(202, {"job_id": jid, "status": "queued"})

        return self._send(404, {"error": "not found"})


def serve(bind="127.0.0.1", port=None):
    token = os.environ.get("LATHE_API_TOKEN", "")
    if not token:
        sys.exit("lathe-api: REFUSING to start — set LATHE_API_TOKEN (no anonymous access).")
    if bind not in ("127.0.0.1", "localhost") and os.environ.get("LATHE_SANDBOX", "") not in ("docker", "docker-ssh"):
        sys.exit("lathe-api: REFUSING to bind %s — non-local bind requires LATHE_SANDBOX=docker|docker-ssh "
                 "(never run remote-submitted plan code in-process)." % bind)
    port = int(port or os.environ.get("LATHE_API_PORT", "8799"))
    httpd = ThreadingHTTPServer((bind, port), Handler)
    print("lathe-api: listening on http://%s:%d/v1  (bearer-token auth required)" % (bind, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nlathe-api: stopped.")


if __name__ == "__main__":
    _bind = "127.0.0.1"
    if "--bind" in sys.argv:
        _bind = sys.argv[sys.argv.index("--bind") + 1]
    serve(bind=_bind)
