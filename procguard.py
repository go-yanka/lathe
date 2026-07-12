"""procguard — make orphaned subprocess explosions impossible on Windows.

Windows has no process groups: when a parent dies (a timeout kill, an unhandled
exception, or the whole terminal/session being torn down) its children are NOT
killed — they orphan and keep running, and anything they spawn keeps spawning.
On 2026-07-12 a backgrounded `run_all.py` whose `cli_matrix` phase launches real
`lathe` builds (→ run_gates → vision_lane_gate → Playwright → Chromium) was torn
down; its ~1000 descendants orphaned and suffocated the machine.

Two mechanisms, used together:

  arm()   Enrolls THIS process in a Windows Job Object flagged
          JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. Every descendant auto-joins the job
          (job membership is inherited). The instant the last handle to the job
          closes — which the OS does when this process dies, by ANY means,
          including TerminateProcess from a session teardown — the kernel
          terminates every process still in the job. This is the guaranteed
          backstop: no descendant can outlive the armed root. No-op off Windows.

  run()   A subprocess.run work-alike whose ONLY difference is: on TimeoutExpired
          it kills the child's ENTIRE tree (taskkill /T), not just the direct
          child. Prevents grandchildren (Playwright/Chromium) leaking on every
          per-step timeout during a long, otherwise-healthy run.

CLI:  python procguard.py reap        # panic button: kill every lingering lathe
                                       # gate/build/Playwright/Chromium orphan
"""
import os
import subprocess
import sys

_JOB = None  # module-global keeps the job handle open for the process lifetime


def arm():
    """Enroll this process in a kill-on-close Job Object. Idempotent.
    Returns True if the guarantee is active, False if it could not be established
    (non-Windows, or the OS refused the assignment — caller still has run())."""
    global _JOB
    if os.name != "nt":
        return False
    if _JOB is not None:
        return True
    try:
        import ctypes
        from ctypes import wintypes as wt

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # 64-bit handles must not be truncated to int — declare the signatures.
        k32.CreateJobObjectW.restype = wt.HANDLE
        k32.CreateJobObjectW.argtypes = [wt.LPVOID, wt.LPCWSTR]
        k32.GetCurrentProcess.restype = wt.HANDLE
        k32.GetCurrentProcess.argtypes = []
        k32.SetInformationJobObject.restype = wt.BOOL
        k32.SetInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, wt.LPVOID, wt.DWORD]
        k32.AssignProcessToJobObject.restype = wt.BOOL
        k32.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]

        class BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wt.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wt.DWORD),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", wt.DWORD),
                        ("SchedulingClass", wt.DWORD)]

        class IOC(ctypes.Structure):
            _fields_ = [("ReadOperationCount", ctypes.c_uint64),
                        ("WriteOperationCount", ctypes.c_uint64),
                        ("OtherOperationCount", ctypes.c_uint64),
                        ("ReadTransferCount", ctypes.c_uint64),
                        ("WriteTransferCount", ctypes.c_uint64),
                        ("OtherTransferCount", ctypes.c_uint64)]

        class EXTENDED(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BASIC),
                        ("IoInfo", IOC),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        JobObjectExtendedLimitInformation = 9
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

        h = k32.CreateJobObjectW(None, None)
        if not h:
            return False
        info = EXTENDED()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(h, JobObjectExtendedLimitInformation,
                                           ctypes.byref(info), ctypes.sizeof(info)):
            return False
        if not k32.AssignProcessToJobObject(h, k32.GetCurrentProcess()):
            # Already in a job that forbids nesting (rare on Win8+). run() still guards.
            return False
        _JOB = h  # keep the handle alive — closing it early would kill us
        return True
    except Exception:
        return False


def kill_tree(pid):
    """Kill a process and every descendant. Best-effort, no external deps."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=30)
        else:
            import signal
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:
        pass


def run(cmd, timeout=None, **kw):
    """subprocess.run work-alike that kills the child's WHOLE tree on timeout.

    Supports the kwargs the harness uses (capture_output, text, encoding, errors,
    cwd, env, stdin). On TimeoutExpired the entire subtree is reaped, then the
    original TimeoutExpired is re-raised so callers keep their existing handling."""
    capture = kw.pop("capture_output", False)
    text = kw.pop("text", False)
    if capture:
        kw.setdefault("stdout", subprocess.PIPE)
        kw.setdefault("stderr", subprocess.PIPE)
    p = subprocess.Popen(cmd, text=text, **kw)
    try:
        out, err = p.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, p.returncode, out, err)
    except subprocess.TimeoutExpired:
        kill_tree(p.pid)
        try:
            p.communicate(timeout=10)
        except Exception:
            pass
        raise


_ORPHAN_PAT = ("run_gates.py", "_lane_gate.py", "engine_v2.py", "run_all.py",
               "cli_matrix.py", "_skelgate_plan", "manifest_contract_gate.py",
               "project_layout_gate.py", "workspace_docs_gate.py", "tristate_gate.py")


def reap():
    """Panic button: kill every lingering lathe gate/build/Playwright/Chromium
    orphan on this machine. Spares claude_proxy.py. Windows-only."""
    if os.name != "nt":
        print("reap: Windows-only")
        return 0
    ps = (
        "$pat='run_gates\\.py|_lane_gate\\.py|engine_v2\\.py|run_all\\.py|cli_matrix\\.py|"
        "_skelgate_plan|manifest_contract_gate\\.py|project_layout_gate\\.py|"
        "workspace_docs_gate\\.py|tristate_gate\\.py|lathe-public|lathe-canonical';"
        "$n=0;"
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" |"
        " Where-Object { $_.CommandLine -and ($_.CommandLine -match $pat) -and"
        " ($_.CommandLine -notmatch 'claude_proxy\\.py') } |"
        " ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop; $n++ } catch {} };"
        "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" |"
        " Where-Object { $_.CommandLine -match 'playwright.driver.node' } |"
        " ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force } catch {} };"
        "Get-Process chrome-headless-shell -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue;"
        "Write-Output ('reaped python: '+$n)"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True)
    print((r.stdout or "").strip())
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reap":
        sys.exit(reap())
    print(__doc__)
