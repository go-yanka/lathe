"""A7 — the whole-product road-ready gate. The fix for "all per-plan gates green != shippable".

Per-plan gates prove each function/page in isolation. They do NOT prove the assembled product
actually BOOTS. Tonight's lesson (your-product app.py corrupted 268x) is exactly this: individual
edits can pass and still leave a server that won't import or start. A7 promotes three checks to
BUILD-FAILING, run in order, fail-closed (stop at the first failure):

  1. import       — the app module imports cleanly (no SyntaxError/ImportError) in a fresh process
  2. boot+health  — the server actually starts and serves a 200 on its health URL
  3. live-E2E     — (optional) a smoke/journey command exits 0 against the running server

`road_ready(stages)` is the generic ordered runner; the `*_stage` helpers build concrete checks.
Subprocess-isolated so a broken target can never crash or hang the harness. No Claude calls.
"""
import os
import subprocess
import sys
import time
import urllib.request


def import_stage(module_name, cwd):
    """Stage: `import module_name` succeeds in a FRESH python process rooted at cwd.
    Returns (ok, detail). Isolated so a SyntaxError in the target can't poison the harness process."""
    def run():
        r = subprocess.run([sys.executable, "-c", f"import {module_name}"],
                           cwd=cwd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return True, f"import {module_name}: ok"
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
        return False, f"import {module_name} FAILED: " + " | ".join(tail)
    return run


def http_ready(url, timeout=20.0, interval=0.3):
    """Poll url until it returns HTTP 200, or timeout. Returns (ok, last_detail)."""
    deadline = time.time() + timeout
    last = "no response"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True, f"200 from {url}"
                last = f"status {r.status}"
        except Exception as e:
            last = str(e)
        time.sleep(interval)
    return False, f"never healthy within {timeout}s ({last})"


def boot_health_stage(cmd, url, cwd=None, timeout=20.0, env=None):
    """Stage: launch `cmd` (e.g. uvicorn), wait for `url` to serve 200, then ALWAYS tear it down.
    Returns (ok, detail). The server is killed in a finally — never left squatting a port."""
    def run():
        proc = None
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ok, detail = http_ready(url, timeout=timeout)
            # If it died before serving, surface that rather than a bare timeout.
            if not ok and proc.poll() is not None:
                detail = f"server exited rc={proc.returncode} before healthy"
            return ok, f"boot+health {url}: {detail}"
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
    return run


def command_stage(name, cmd, cwd=None, timeout=300, env=None):
    """Stage: run a command (e.g. a live-E2E smoke run); ok iff it exits 0. Returns (ok, detail)."""
    def run():
        try:
            r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, f"{name} TIMEOUT after {timeout}s"
        if r.returncode == 0:
            return True, f"{name}: exit 0"
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
        return False, f"{name} FAILED rc={r.returncode}: " + " | ".join(tail)
    return run


def road_ready(stages):
    """Run (name, stage_callable) pairs IN ORDER, fail-closed (stop at first failure).
    Each stage_callable() -> (ok: bool, detail: str). Returns
    {'ok': bool, 'results': [{'name','ok','detail'}], 'failed': name|None}."""
    results = []
    for name, stage in stages:
        try:
            ok, detail = stage()
        except Exception as e:
            ok, detail = False, f"{name} raised: {e}"
        results.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            return {"ok": False, "results": results, "failed": name}
    return {"ok": True, "results": results, "failed": None}
