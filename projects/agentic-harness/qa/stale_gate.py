"""STALE / RETIREMENT GATE — keep the agentic-harness tree pristine.

Ported from the canonical Helix harness (qa/stale_gate.py, owner-requested 2026-06-25) to the agentic-harness
project on 2026-06-29 so the SAME cleanup discipline is ENFORCED here, not just available in the engine.

The recurring bug it prevents: backup/duplicate/superseded files linger in the source dirs, so the WRONG
version gets picked up later and stale artifacts confuse the model about what to fix (the multi-DB mess was
exactly this — no cleanup, so leftovers accumulated). This gate FAILS the build if a retire-marker file is
still in a main dir, forcing decide-then-archive: move it to _archive/<date>-<reason>/ (kept, not deleted).

  python qa/stale_gate.py            # gate mode -> exit 1 if any stale file in the main tree
  python qa/stale_gate.py --list     # just list candidates
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # projects/agentic-harness
MAIN_DIRS = ["tools", "plans"]                                      # the agentic-harness source surfaces
SKIP = ("_archive", "_legacy", "_retired", "_fn_fails", "__pycache__", ".git")
# names that must NOT live in the main tree — backups / dups / superseded versions
# PR#1 v2.8.1 #8-F8: broadened — was too narrow (only _v1/_v2_old; missed _v3+, _final/_new/_prev/_deprecated,
# "(copy)"). NOTE: bare trailing-digit names (utils2.py) are deliberately NOT matched here — too many valid
# files end in a digit; that staleness is better caught by the capability registry (which name is 'live') than
# by a filename regex.
RETIRE_PAT = re.compile(
    r"(_backup|\.bak|_bak\b|_old\b|_v\d+_old|_v\d+\b|_copy\b|_copy\d+|copy\d|\(copy\)|_final\b|_new\b|_prev\b|"
    r"_deprecated\b|\.orig$|~$|\.tmp$)", re.I)

def candidates():
    out = []
    for d in MAIN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dp, dns, fns in os.walk(base):
            if any(s in dp.replace("\\", "/").split("/") for s in SKIP):
                continue
            for fn in fns:
                if fn.endswith(".pins.json.tmp"):
                    continue                                  # the engine's OWN atomic pin-write temp (transient, removed by os.replace) — not stale clutter
                if RETIRE_PAT.search(fn):
                    out.append(os.path.relpath(os.path.join(dp, fn), ROOT).replace("\\", "/"))
    return sorted(out)

if __name__ == "__main__":
    c = candidates()
    if "--list" in sys.argv:
        print("\n".join(c) or "(none)"); sys.exit(0)
    if not c:
        print("stale_gate: clean — no backup/dup/superseded files in tools/ or plans/"); sys.exit(0)
    print("STALE FILES in the agentic-harness tree (retire to _archive/<date>-<reason>/, then re-run):")
    for f in c:
        print("  RETIRE  " + f)
    print("\nDecide-then-archive: move each to _archive/, write a one-line reason. Keeps the tree pristine.")
    sys.exit(1)
