"""resource_dups_gate — catch DUPLICATE data resources the name-pattern stale_gate misses.

The recurring maintainability bug (owner, 2026-06-30): the harness ends up with several databases / resource
files of the SAME basename in different folders (e.g. two harness.db) instead of one canonical store that gets
enhanced. stale_gate.py only catches files NAMED like backups (_old/_bak/_v2); it does not see two legitimately-
named-but-duplicated resources. This gate does, using the harness-BUILT pure helper tools/duplicate_basenames.py.

  python qa/resource_dups_gate.py            # gate mode -> exit 1 if any resource basename is duplicated
  python qa/resource_dups_gate.py --list     # just print the duplicate groups

Scope: data/resource files (*.db, *.sqlite, *.sqlite3) under the project, excluding throwaway/vendor dirs.
Kept tight on purpose (resources only, not every .py) so it is high-signal and never false-fails a build.
"""
import os
import sys

_QA = os.path.dirname(os.path.abspath(__file__))
_INNER = os.path.dirname(_QA)                       # projects/agentic-harness
_TOOLS = os.path.join(_INNER, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
from duplicate_basenames import duplicate_basenames  # the harness-built detector

_RESOURCE_EXT = (".db", ".sqlite", ".sqlite3")
# NOTE: do NOT skip "qa" — the gate scope is .db/.sqlite only, and a stray duplicate DB dropped under qa/
# (exactly the "multi-DB mess" this gate exists to catch) must stay visible. Skipping qa/ blinded the gate.
_SKIP_DIRS = {".git", ".github", "__pycache__", "node_modules", "_archive", ".venv", "venv"}


def _resource_paths(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.lower().endswith(_RESOURCE_EXT):
                out.append(os.path.join(dirpath, fn))
    return out


def main(argv):
    root = _INNER
    dups = duplicate_basenames(_resource_paths(root))
    if "--list" in argv:
        for base, paths in sorted(dups.items()):
            print("%s:" % base)
            for p in paths:
                print("  " + p)
        return 0
    if not dups:
        print("resource_dups_gate: clean - one canonical copy of each data resource (no duplicate .db/.sqlite)")
        return 0
    print("resource_dups_gate: DUPLICATE resources found - consolidate to ONE canonical store and enhance it:")
    for base, paths in sorted(dups.items()):
        print("  %s appears in %d places:" % (base, len(paths)))
        for p in paths:
            print("    " + p)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
