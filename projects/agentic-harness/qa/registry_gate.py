"""registry_gate — make capability DIVERGENCE a build failure, not a latent trap.

Fails (exit 1) if the capability registry (capabilities.json) is inconsistent: an invalid status, a capability
that is superseded yet still 'live', two 'live' entries sharing one canonical artifact, or a live/designed
capability whose canonical file is missing on disk. Clean registry -> exit 0. Empty/absent registry -> exit 0
(opt-in: a project that hasn't declared capabilities isn't penalised).

  python qa/registry_gate.py            # gate mode
  python qa/registry_gate.py --list     # print the live capability map
"""
import os
import sys

_QA = os.path.dirname(os.path.abspath(__file__))
_INNER = os.path.dirname(_QA)
_TOOLS = os.path.join(_INNER, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
import registry


def main(argv):
    reg = registry.load()
    if "--list" in argv:
        for name, e in sorted((reg or {}).items()):
            if isinstance(e, dict) and e.get("status") == "live":
                print("  %-26s -> %s  (%s)" % (name, e.get("canonical", "?"), e.get("entrypoint", "")))
        return 0
    probs = registry.audit()
    if not probs:
        n = sum(1 for e in (reg or {}).values() if isinstance(e, dict) and e.get("status") == "live")
        print("registry_gate: clean - %d capabilities, one canonical 'live' each, all present." % n)
        return 0
    print("registry_gate: capability registry DIVERGENCE (fix capabilities.json):")
    for p in probs:
        print("  - " + p)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
