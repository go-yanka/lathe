"""failure_registry_gate.py — C4: enforce the adversarial ratchet.

Invariant: every failure CLASS in tools/failure_modes.py that claims a gate MUST have that gate actually
wired into the standing suite (run_gates.py CHECKS). A class can't claim to be caught by a gate that isn't
running. Open holes (gate=None) are printed LOUDLY every run — so a known-but-unguarded failure is visible,
never a silent gap. This is what makes "we keep adding them to the gates" self-checking: add a class, you
must add (and wire) its gate, or this gate tells you the coverage is a lie.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import re
import sys

QA = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(QA), "tools")
sys.path.insert(0, TOOLS)

import failure_modes as fm   # noqa: E402


def main():
    # the gate names actually wired into the standing suite
    run_gates = open(os.path.join(QA, "run_gates.py"), encoding="utf-8").read()
    wired = set(re.findall(r'\(\s*"([a-z_]+)"\s*,\s*os\.path\.join\(QA', run_gates))
    wired.add("regression")  # the umbrella name

    claimed = fm.guarded()
    missing = [f for f in claimed if f["gate"] not in wired]
    if missing:
        print("failure-registry gate: FAIL — these failure classes claim a gate that is NOT wired into run_gates:")
        for f in missing:
            print("   %-28s -> claims gate '%s' (not in the standing suite)" % (f["id"], f["gate"]))
        sys.exit(1)

    holes = fm.open_holes()
    print("failure-registry gate: %d guarded class(es) all have a wired gate; %d OPEN hole(s) tracked:"
          % (len(claimed), len(holes)))
    for f in holes:
        print("   [OPEN] %-28s %s" % (f["id"], f["klass"]))
    sys.exit(0)


if __name__ == "__main__":
    main()
