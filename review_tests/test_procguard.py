"""BEHAVIORAL TEST — procguard.run's timeout path must NOT kill its own caller.

Regression (reviewer finding, 2026-07-13): procguard.run() Popen'd the child in the
CALLER's process group and, on timeout, kill_tree() did
    os.killpg(os.getpgid(child), SIGKILL)
which on Linux/macOS SIGKILLs the caller's WHOLE group — including the caller.
run_gates routes every HEAVY gate through procguard.run with GATE_TIMEOUT, so a gate
timeout would kill run_gates itself (the opposite of the intended fix). The Windows
taskkill /T path was always fine; the bug was the POSIX killpg path.

This proves, on whatever platform it runs:
  1. procguard.run raises TimeoutExpired TO the caller,
  2. the caller SURVIVES to run code after `except` (prints a sentinel, exits 0) —
     a caller whose process group was SIGKILLed produces neither,
  3. the timed-out child is actually gone (no orphan).

The caller runs as its OWN subprocess so that if procguard nukes the caller's group,
this test observes it as a missing sentinel / signal exit code rather than dying too.

On POSIX this is load-bearing against the exact bug: revert the fix (remove the
os.name passthrough in run()) and the caller is group-killed -> assertions 1 & 2 FAIL.

Run:  python review_tests/test_procguard.py       (repo root)
"""
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
sys.path.insert(0, ROOT)
import procguard
fails = []


def check(name, ok, detail=""):
    print("  %-58s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


def alive(pid):
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid], capture_output=True, text=True)
        return str(pid) in (r.stdout or "")
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


pidfile = tempfile.mktemp(prefix="pg_child_")
# child records its own pid, then sleeps far past the timeout
child_code = ("import os,time;"
              "open(%r,'w').write(str(os.getpid()));"
              "time.sleep(60)" % pidfile)

# caller: runs procguard.run on that child with a SHORT timeout, then MUST reach the
# sentinel line after the except. If its process group is killed, it never does.
caller_src = (
    "import sys, subprocess\n"
    "sys.path.insert(0, %r)\n"
    "import procguard\n"
    "rc = 99\n"
    "try:\n"
    "    procguard.run([%r, '-c', %r], timeout=2, capture_output=True, text=True)\n"
    "except subprocess.TimeoutExpired:\n"
    "    rc = 0\n"
    "except Exception:\n"
    "    rc = 2\n"
    "print('CALLER_SENTINEL', rc)\n"
    "sys.exit(rc)\n"
) % (ROOT, PY, child_code)

caller_file = tempfile.mktemp(prefix="pg_caller_", suffix=".py")
open(caller_file, "w", encoding="utf-8").write(caller_src)

try:
    proc = subprocess.run([PY, caller_file], capture_output=True, text=True, timeout=40)
    out = (proc.stdout or "") + (proc.stderr or "")
    check("caller received TimeoutExpired (not group-killed)", "CALLER_SENTINEL 0" in out,
          out.strip()[-200:])
    check("caller exited 0 — survived the timeout", proc.returncode == 0, "rc=%s" % proc.returncode)

    time.sleep(1)
    child_pid = None
    try:
        child_pid = int(open(pidfile).read().strip())
    except Exception:
        pass
    check("child pid was recorded", child_pid is not None)
    if child_pid is not None:
        a = alive(child_pid)
        check("timed-out child is dead (no orphan)", not a, "pid %s alive" % child_pid)
        if a:  # never leak from the test itself
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(child_pid), "/T", "/F"], capture_output=True)
                else:
                    os.kill(child_pid, 9)
            except Exception:
                pass
finally:
    for f in (pidfile, caller_file):
        try:
            os.remove(f)
        except Exception:
            pass

# Platform-independent proof the FIX is present and load-bearing on EVERY OS: when
# os.name != "nt", run() must be a strict passthrough to subprocess.run and must NOT
# take the Popen+kill_tree path (whose POSIX killpg is what nuked the caller). Revert
# the fix (drop the `if os.name != "nt"` gate) and this flips even on Windows, because
# run() would then Popen unconditionally.
_real_run, _real_popen, _saved_name = procguard.subprocess.run, procguard.subprocess.Popen, procguard.os.name
_calls = {"run": 0}


def _spy_run(*a, **k):
    _calls["run"] += 1
    return subprocess.CompletedProcess(a[0] if a else k.get("args"), 0, "", "")


def _spy_popen(*a, **k):
    raise AssertionError("Popen used on the off-Windows path — passthrough gate is gone")


try:
    procguard.os.name = "posix"
    procguard.subprocess.run = _spy_run
    procguard.subprocess.Popen = _spy_popen
    procguard.run([PY, "-c", "pass"], timeout=5, capture_output=True, text=True)
    check("off-Windows: run() is a strict subprocess.run passthrough (no Popen path)",
          _calls["run"] == 1)
except AssertionError as e:
    check("off-Windows: run() is a strict subprocess.run passthrough (no Popen path)", False, str(e))
finally:
    procguard.os.name = _saved_name
    procguard.subprocess.run = _real_run
    procguard.subprocess.Popen = _real_popen

print("\nprocguard timeout-path acceptance: %s"
      % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
