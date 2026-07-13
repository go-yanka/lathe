"""ACCEPTANCE — #39/#40 (BEHAVIORAL): the standing-regression retry policy, driven through run_gates.main()
with a STUB gate — not a source grep.

#39: retries must be scoped to the HEAVY browser gates. A DETERMINISTIC gate that fails must fail CLOSED on the
     first failure (no retry that could clear an intermittently-real bug); a HEAVY gate that flakes IS retried.
#40: `_int_env` must not crash the whole regression on a blank/typo/negative GATE_RETRIES/GATE_TIMEOUT.

The stub gate fails on its FIRST invocation and passes afterwards (a classic flake), tracked by a counter file,
so "was it retried?" is observable as the invocation count. Model-free. Run: python review_tests/test_gate_hardening.py
"""
import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RG_PATH = os.path.join(ROOT, "projects", "agentic-harness", "qa", "run_gates.py")
fails = []


def check(name, ok, detail=""):
    print("  %-64s %s %s" % (name, "PASS" if ok else "FAIL", detail if not ok else ""))
    if not ok:
        fails.append(name)


# load run_gates as a module (its main() only runs under __main__, so import is side-effect-free)
spec = importlib.util.spec_from_file_location("run_gates_mod", RG_PATH)
rg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rg)

# --- #40: _int_env is crash-proof ---
for env, default, want, label in [(None, 5, 5, "unset->default"), ("", 5, 5, "blank->default"),
                                  ("foo", 5, 5, "typo->default"), ("-1", 5, 5, "negative->default"),
                                  ("3", 5, 3, "valid->parsed"), ("0", 5, 0, "zero->honored")]:
    os.environ.pop("GX", None)
    if env is not None:
        os.environ["GX"] = env
    got = rg._int_env("GX", default)
    check("#40 _int_env %s" % label, got == want, "got %r" % got)
    os.environ.pop("GX", None)

td = tempfile.mkdtemp(prefix="gate_")
counter = os.path.join(td, "count.txt")
stub = os.path.join(td, "stub_gate.py")
open(stub, "w", encoding="utf-8").write(
    "import os, sys\n"
    "cf = os.environ['STUB_COUNTER']\n"
    "n = (int(open(cf).read() or '0') if os.path.exists(cf) else 0) + 1\n"
    "open(cf, 'w').write(str(n))\n"
    "sys.exit(1 if n == 1 else 0)   # fail the FIRST run (flake), pass after\n")
os.environ["STUB_COUNTER"] = counter


def run_main_with(checks, full):
    open(counter, "w").write("0")
    rg.CHECKS = checks
    os.environ["LATHE_GATE_FULL"] = "1" if full else "0"
    os.environ["GATE_RETRIES"] = "2"
    try:
        rg.main()
        rc = 0
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    return rc, int(open(counter).read())


# --- #39a: a DETERMINISTIC (non-HEAVY) gate fails CLOSED and is NOT retried ---
rcA, nA = run_main_with([("stub_det", stub)], full=False)
check("#39 a deterministic gate fails CLOSED (regression exit 1)", rcA == 1, "rc=%r" % rcA)
check("#39 a deterministic gate is NOT retried (ran exactly once)", nA == 1, "ran %d times" % nA)

# --- #39b: a HEAVY gate (skeleton_lane) IS retried, so a genuine flake clears ---
rcB, nB = run_main_with([("skeleton_lane", stub)], full=True)     # skeleton_lane is in rg.HEAVY
check("#39 a HEAVY gate IS retried (flake clears -> exit 0)", rcB == 0, "rc=%r" % rcB)
check("#39 a HEAVY gate ran more than once (retried)", nB >= 2, "ran %d times" % nB)

os.environ.pop("LATHE_GATE_FULL", None)
os.environ.pop("GATE_RETRIES", None)
os.environ.pop("STUB_COUNTER", None)
import shutil
shutil.rmtree(td, ignore_errors=True)
print("\ngate-hardening #39/#40 acceptance: %s" % ("ALL PASS" if not fails else "FAILED: %s" % ", ".join(fails)))
sys.exit(0 if not fails else 1)
