"""registry — the capability SOURCE OF TRUTH. Answers "which artifact is LIVE for capability X" by LOOKUP,
not by grep/trace. This is the fix for the duplication/divergence trap (N copies of the same thing, nothing
says which is real). The registry binds:  capability -> {canonical, entrypoint, status, supersedes}.

  status: 'live'     = THE wired, authoritative implementation (exactly one per capability)
          'designed' = built but NOT wired (so docs can't imply it's live — the SQL-matcher trap)
          'retired'  = superseded; kept for history, never the answer

The registry file is <project>/capabilities.json. Introspection: `lathe whatis <capability>`.
Enforcement: registry_gate.py fails a build on >1 live / superseded-but-live / duplicate live canonical /
canonical missing on disk — so divergence is a GATE FAILURE, not a latent trap.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))            # tools/
_INNER = os.path.dirname(_HERE)                               # projects/agentic-harness
REGISTRY_PATH = os.path.join(_INNER, "capabilities.json")


def load(path=None):
    """A MISSING registry is legitimately empty ({}). A PRESENT-but-broken registry is NOT empty — it's an
    error that must surface as a gate failure, never be swallowed into a false-clean {} (the source-of-truth
    file being corrupt is exactly the divergence trap this module exists to catch)."""
    try:
        with open(path or REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError, ValueError) as e:
        return {"__error__": "capabilities.json unreadable/unparseable: %s" % e}


def whatis(capability, path=None):
    """The single authoritative entry for a capability (or None). Lookup, not trace."""
    return load(path).get(capability)


def audit(path=None):
    """Every registry problem: internal consistency (harness-built registry_violations) + on-disk reality
    (a live/designed capability whose canonical artifact doesn't exist). Returns a sorted list of strings."""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from registry_violations import registry_violations       # the harness-BUILT pure auditor
    from spine_helpers import treat_missing_as_uninitialized   # B2: harness-built — a missing runtime DB is uninitialized, not divergence
    reg = load(path)
    if isinstance(reg, dict) and "__error__" in reg:
        return ["registry: " + reg["__error__"]]                # broken file -> ONE loud violation, not a false-clean
    probs = list(registry_violations(reg))
    for name, entry in (reg or {}).items():
        if isinstance(entry, dict) and entry.get("status") in ("live", "designed"):
            can = entry.get("canonical", "")
            if not can:
                probs.append("%s: %s without a canonical artifact" % (name, entry.get("status")))
                continue
            full = can if os.path.isabs(can) else os.path.join(_INNER, can)
            if not os.path.exists(full) and not treat_missing_as_uninitialized(can):   # B2: a runtime DB (e.g. harness.db) just isn't created yet
                probs.append("%s: canonical missing on disk (%s)" % (name, can))
    return sorted(probs)
