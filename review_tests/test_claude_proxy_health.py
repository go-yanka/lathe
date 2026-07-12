"""ACCEPTANCE — issue #46: claude_proxy resolves CLAUDE_BIN from PATH and /health PROBES the binary.

Before: CLAUDE_BIN defaulted to a hardcoded Windows path (%APPDATA%\\npm\\claude.cmd) that doesn't exist
off-Windows, and /health just echoed that string as {"status":"ok"} — so the proxy looked up while every
completion failed. After: CLAUDE_BIN resolves via shutil.which("claude") when unset, and /health actually
probes the binary (unhealthy + 503 when it's missing).

Each case imports claude_proxy in a SUBPROCESS with a controlled env (CLAUDE_BIN is resolved at import time),
so the checks are deterministic and need no network / no claude CLI.

  Run:  python review_tests/test_claude_proxy_health.py     (repo root)
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(name, ok, detail=""):
    print("  %-60s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


_PROBE = (
    "import asyncio, json, sys, shutil\n"
    "sys.path.insert(0, r%r)\n"
    "import claude_proxy as P\n"
    "r = asyncio.run(P.health())\n"
    "body = json.loads(r.body)\n"
    "print(json.dumps({'bin': P.CLAUDE_BIN, 'status': body['status'], 'code': r.status_code,\n"
    "                  'healthy': P._bin_healthy(), 'which': shutil.which('claude') or ''}))\n"
) % ROOT


def probe(env_extra):
    env = dict(os.environ, **env_extra)
    r = subprocess.run([sys.executable, "-c", _PROBE], cwd=ROOT, capture_output=True, text=True, env=env, timeout=90)
    line = [x for x in (r.stdout or "").splitlines() if x.strip().startswith("{")]
    if not line:
        return None, (r.stdout + r.stderr)[-400:]
    return json.loads(line[-1]), ""


# A) a NON-EXISTENT bin must report unhealthy + 503 (the /health probe — before the fix it echoed "ok"/200)
bad = os.path.join(ROOT, "definitely_not_a_real_claude_binary_zzz")
a, err = probe({"CLAUDE_BIN": bad})
check("missing bin -> /health status 'unhealthy'", bool(a) and a["status"] == "unhealthy", err or (a or {}))
check("missing bin -> /health HTTP 503 (not a false 200)", bool(a) and a["code"] == 503, (a or {}).get("code"))
check("missing bin -> _bin_healthy() is False", bool(a) and a["healthy"] is False, (a or {}))

# B) a REAL, existing file resolves healthy + 200 (use this interpreter as a stand-in executable path)
good, err = probe({"CLAUDE_BIN": sys.executable})
check("real bin -> /health status 'ok'", bool(good) and good["status"] == "ok", err or (good or {}))
check("real bin -> /health HTTP 200", bool(good) and good["code"] == 200, (good or {}).get("code"))

# C) with CLAUDE_BIN UNSET, resolution consults PATH (shutil.which) instead of hardcoding the Windows shim
env_noenv = {k: v for k, v in os.environ.items() if k != "CLAUDE_BIN"}
c, err = probe({k: env_noenv[k] for k in env_noenv} if False else {"CLAUDE_BIN": ""})
# CLAUDE_BIN="" is falsy -> the code path is `os.environ.get("CLAUDE_BIN") or shutil.which(...)`, same as unset
if c and c.get("which"):
    check("unset CLAUDE_BIN resolves to which('claude') (PATH-aware)", c["bin"] == c["which"], (c or {}))
else:
    check("unset CLAUDE_BIN: PATH has no claude — resolution didn't crash (skipped which-eq)", bool(c), (c or {}))

print("\nclaude_proxy health (#46) acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
