"""ACCEPTANCE — the two shakedown SECURITY findings:

  #35  LATHE_SANDBOX=docker-ssh must NOT be silently dropped to the trusted in-proc path.
       engine_v2._sandbox() has to RECOGNISE docker-ssh (load sandbox.py, which routes it to a
       remote fail-closed container) instead of returning None (= run UNSANDBOXED).

  #36  cmd_ack / cmd_assume / cmd_trace exec the plan module (exec_module) — so they must run the
       SAME data-safety RCE guard as build/verify. A plan with a top-level side effect is both
       guaranteed-rejected by plan_validator AND a live RCE probe: if the guard is missing the plan
       EXECUTES and drops a PWNED sentinel; if present, the command REFUSES and no sentinel appears.

Model-free. Run:  python review_tests/test_security_exec_guards.py     (repo root)
"""
import ast
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
fails = []


def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


# ---- #35: docker-ssh is a recognised sandbox mode (not a silent unsandboxed downgrade) ----
# engine_v2.py runs a build at import time (no __main__ guard), so we can't import it. Instead AST-extract
# the real _sandbox() source and exec it in isolation — a behavioral test of the shipped function.
ENGINE = os.path.join(ROOT, "engine_v2.py")
_src = open(ENGINE, encoding="utf-8").read()
_fn = next((n for n in ast.parse(_src).body if isinstance(n, ast.FunctionDef) and n.name == "_sandbox"), None)
if _fn is None:
    check("#35 _sandbox() found in engine_v2.py", False)
else:
    import importlib as _il
    _ns = {"os": os, "sys": sys, "importlib": _il, "__file__": ENGINE, "_SB": None}
    exec(compile(ast.Module(body=[_fn], type_ignores=[]), ENGINE, "exec"), _ns)
    for _mode in ("docker-ssh", "docker_ssh"):
        os.environ["LATHE_SANDBOX"] = _mode
        _ns["_SB"] = None
        try:
            _sb = _ns["_sandbox"]()
            ok = _sb is not None                       # None == silently dropped to trusted in-proc (UNSANDBOXED)
            check("#35 LATHE_SANDBOX=%s loads the sandbox (not silently unsandboxed)" % _mode, ok,
                  "returned None -> would run UNSANDBOXED")
        except SystemExit as e:
            # sys.exit only fires if sandbox.py is unresolvable — still proves docker-ssh was RECOGNISED
            check("#35 LATHE_SANDBOX=%s is recognised (not silently unsandboxed)" % _mode, True)
        finally:
            os.environ.pop("LATHE_SANDBOX", None)


# ---- #36: ack/assume/trace refuse an unsafe (exec'd) plan, same as build ----
def run_guard(cmd, plan_path, sentinel):
    if os.path.exists(sentinel):
        os.remove(sentinel)
    r = subprocess.run([PY, os.path.join(ROOT, "lathe.py"), cmd, plan_path],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    executed = os.path.exists(sentinel)          # the RCE actually fired
    if os.path.exists(sentinel):
        os.remove(sentinel)
    refused = ("REFUSING" in (r.stdout or "") + (r.stderr or "")) and r.returncode != 0
    return refused, executed


for cmd in ("ack", "assume", "trace"):
    with tempfile.TemporaryDirectory() as td:
        sentinel = os.path.join(td, "PWNED")
        plan = os.path.join(td, "evil_plan.py")
        # top-level side effect => plan_validator rejects it AND it is a real RCE if exec'd
        with open(plan, "w", encoding="utf-8") as f:
            f.write("open(%r, 'w').write('x')\n" % sentinel)
            f.write("MODULE_NAME = 'm'\n")
            f.write("OUT_DIR = '.'\n")
            f.write("FUNCTIONS = [{'name': 'f', 'prompt': 'p', 'tests': ['assert True']}]\n")
        refused, executed = run_guard(cmd, plan, sentinel)
        check("#36 cmd_%s REFUSES an unsafe (exec'd) plan" % cmd, refused)
        check("#36 cmd_%s did NOT execute the plan's RCE payload" % cmd, not executed)


# sanity: a SAFE plan must still be accepted by the guard (no false-refusal of legitimate plans)
with tempfile.TemporaryDirectory() as td:
    plan = os.path.join(td, "good_plan.py")
    with open(plan, "w", encoding="utf-8") as f:
        f.write("MODULE_NAME = 'm'\n")
        f.write("OUT_DIR = %r\n" % td)
        f.write("FUNCTIONS = [{'name': 'f', 'prompt': 'p', 'tests': ['assert True']}]\n")
    r = subprocess.run([PY, os.path.join(ROOT, "lathe.py"), "trace", plan],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    # must NOT be refused by the data-safety guard (it may no-op for other reasons, but never "REFUSING ... data-safe")
    check("#36 a legitimate plan is NOT false-refused by the guard",
          "not data-safe" not in ((r.stdout or "") + (r.stderr or "")))

print("\nsecurity exec-guards acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
