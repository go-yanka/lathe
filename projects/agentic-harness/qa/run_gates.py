"""STANDING REGRESSION for the agentic-harness project.

The engine (engine_v2.py) runs this after every successful build (it resolves projects/<proj>/qa/run_gates.py
from the plan path — see the decoupling fix 2026-06-29). A non-zero exit makes the build RED, so a build that
leaves the tree dirty cannot ship. Keep it FAST and deterministic — it runs on every plan.

Currently enforces:
  - stale_gate: no backup/dup/superseded files linger in tools/ or plans/ (cleanup discipline)

Add more standing checks here as the harness grows (e.g. no two tools exporting the same MODULE_NAME).
"""
import os, subprocess, sys

QA = os.path.dirname(os.path.abspath(__file__))
CHECKS = [("tree_no_stale_dups", os.path.join(QA, "stale_gate.py")),
          ("no_duplicate_resources", os.path.join(QA, "resource_dups_gate.py")),  # one canonical DB/resource, not several
          ("capability_registry", os.path.join(QA, "registry_gate.py")),          # one 'live' canonical per capability
          ("pristine_tree", os.path.join(QA, "pristine_gate.py")),                 # no corrupt/half-written files linger
          ("lint_no_real_bugs", os.path.join(QA, "lint_gate.py")),                 # ruff: no undefined-name/syntax/format defects in generated code
          ("docs_not_drifted", os.path.join(QA, "docs_drift_gate.py")),            # every CLI command documented with an example in LATHE_COMMANDS.md
          ("env_not_drifted", os.path.join(QA, "env_drift_gate.py")),               # every env var the code reads is documented in env_catalog.py (lathe env)
          ("manifest_contract", os.path.join(QA, "manifest_contract_gate.py")),     # #12: every invocation emits a complete, un-skippable manifest (T2-T6)
          ("spine_enforced", os.path.join(QA, "spine_gate.py"))]                     # #12 P1: guard-forge/skill-subprocess/bypass attacks all defeated (P1-P5)

def main():
    failed = []
    for name, path in CHECKS:
        if not os.path.exists(path):
            # #12 (PR#7 round-3 finding): a MISSING gate file used to be silently skipped while the run
            # still printed "regression clean" — a vacuous green. A registered gate that is absent is a FAIL.
            print("%-22s FAIL :: gate file missing: %s" % (name, os.path.basename(path)))
            failed.append(name + "(missing)")
            continue
        r = subprocess.run([sys.executable, path], capture_output=True, text=True)
        tag = "PASS" if r.returncode == 0 else "FAIL"
        last = (r.stdout.strip().splitlines() or [""])[-1]
        print("%-22s %s :: %s" % (name, tag, last))
        if r.returncode != 0:
            failed.append(name)
    if failed:
        print("REGRESSION: " + ", ".join(failed)); sys.exit(1)
    print("regression clean (%d checks)" % len(CHECKS)); sys.exit(0)

if __name__ == "__main__":
    main()
