"""lint_gate — catch REAL bugs in generated modules with ruff (not style). The local model occasionally emits
code with an undefined name, a redefinition, a broken %-format, or a syntax slip; those pass the unit tests
only if the tests miss them, then ship. This gate hard-fails on the pyflakes/error-level rules that mean an
ACTUAL DEFECT (F* minus the unused-import/var noise, plus E9 syntax). Unused imports/vars are reported as an
advisory (generated code needn't be PEP8-pretty; we do NOT hand-edit generated modules to satisfy style).

Optional dependency: if ruff isn't installed the gate SKIPS (never fails a build for a missing linter).
  python qa/lint_gate.py          # gate: exit 1 on any real-bug finding in tools/
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # projects/agentic-harness
TOOLS = os.path.join(ROOT, "tools")
_HARD = ["--select", "F,E9", "--ignore", "F401,F841"]                # real bugs; F401/F841 = unused (advisory)


def main(argv):
    if shutil.which("ruff") is None:
        print("lint_gate: ruff not installed (pip install ruff) — SKIPPED (optional dep)"); return 0
    hard = subprocess.run(["ruff", "check"] + _HARD + ["--quiet", TOOLS], capture_output=True, text=True)
    adv = subprocess.run(["ruff", "check", "--select", "F401,F841", "--quiet", TOOLS], capture_output=True, text=True)
    adv_n = len([l for l in (adv.stdout or "").splitlines() if ":" in l])
    if hard.returncode == 0:
        note = "" if not adv_n else "  (advisory: %d unused import/var in generated modules)" % adv_n
        print("lint_gate: clean — no undefined-name/syntax/format defects in tools/.%s" % note)
        return 0
    print("lint_gate: REAL-BUG findings in generated modules (undefined name / syntax / format):")
    print((hard.stdout + hard.stderr).strip()[:2000])
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
