"""standing_team.py (#50) — the PERMANENT senior crew: the lifecycle that makes the Application Architect,
Senior Developer, and Senior Tester standing team members (the Advocate pattern) instead of stateless one-shot
lenses.

The raw talent already exists (the CE reviewers + the catalog's architect/dev/test roles), and the Advocate
already proves the pattern (`tools/advocate.py`: seeded with intent, holds a charter + evolving memory, stays
for the whole run). This module gives the three judging seniors that same permanence:

  - a **charter** seeded per project (goal + #48 framing),
  - an **evolving memory** carried across stages,
  - **engagement** at the right stage using the role's SOUL (`ce_personas/<role>.md`),
  - a **severity-routed verdict** (P0-P3) so it feeds the review gate (#51).

The pure parts (roster, charter seed, prompt build, verdict parse, memory update) are model-free and testable;
`engage()` takes the analyst callable so the frontier call stays injectable.
"""
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERSONAS = os.path.join(os.path.dirname(_HERE), "ce_personas")

# The standing crew. Each is a PERMANENT, charter-holding judge (unlike the stateless CE lenses). `engages_at`
# names the stages it presides over; `can_block` is its authority at the review gate (P0/P1). The Advocate is
# the fourth standing member (intent) and lives in advocate.py — it sits above these three.
ROLES = [
    {"key": "application-architect", "title": "Application / System Architect",
     "soul": "application-architect.md", "owns": "decomposition, module boundaries, file/folder layout, cross-cutting design",
     "engages_at": ["architecture", "review", "release"], "can_block": True},
    {"key": "senior-developer", "title": "Senior Developer",
     "soul": "senior-developer.md", "owns": "cross-module consistency, reuse, implementation patterns, seam integrity",
     "engages_at": ["build", "review"], "can_block": True},
    {"key": "senior-tester", "title": "Senior Tester / QA Lead",
     "soul": "senior-tester.md", "owns": "test strategy + coverage across the project (proves the GOAL, not just units)",
     "engages_at": ["spec", "review", "release"], "can_block": True},
]

_BY_KEY = {r["key"]: r for r in ROLES}
_SEV = ("P0", "P1", "P2", "P3", "NONE")


def roster():
    """The standing crew + whether each role's SOUL file is present (a role without a real soul is hollow — #50)."""
    return [dict(r, soul_present=os.path.isfile(os.path.join(_PERSONAS, r["soul"]))) for r in ROLES]


def for_stage(stage):
    """The standing roles that preside over `stage` (e.g. 'architecture' -> the Architect)."""
    return [r for r in ROLES if stage in r["engages_at"]]


def load_soul(role_key):
    r = _BY_KEY.get(role_key)
    if not r:
        return ""
    try:
        return open(os.path.join(_PERSONAS, r["soul"]), encoding="utf-8").read()
    except OSError:
        return ""


def seed(goal, framing=""):
    """The project CHARTER the whole crew is seeded with at kickoff — the yardstick they judge against for the
    entire run (the Advocate-permanence pattern). Returned as a small dict; carried alongside per-role memory."""
    return {"goal": (goal or "").strip(), "framing": (framing or "").strip()}


def _prompt(role_key, stage, artifact, charter, memory):
    soul = load_soul(role_key) or ("You are the %s." % _BY_KEY.get(role_key, {}).get("title", role_key))
    mem = ("\n\n--- YOUR MEMORY SO FAR (this project) ---\n%s" % memory) if memory else ""
    fr = ("\n- framing: %s" % charter.get("framing")) if (charter or {}).get("framing") else ""
    return (
        "%s\n\n--- PROJECT CHARTER (seeded at kickoff — your yardstick) ---\n- goal: %s%s%s\n\n"
        "--- STAGE ---\nYou are engaged at the '%s' stage.\n\n--- ARTIFACT TO JUDGE ---\n%s\n\n"
        "Judge it against the CHARTER and your standing role. Reply in EXACTLY this shape (one line each):\n"
        "VERDICT: approve | concern | block\n"
        "SEVERITY: P0 | P1 | P2 | P3 | none\n"
        "NOTE: <one sentence — the single most important structural/quality/coverage point>"
        % (soul, (charter or {}).get("goal", ""), fr, mem, stage, artifact)
    )


def parse_verdict(raw):
    """Pure: extract {verdict, severity, note} from a standing role's reply. Defaults are conservative (a
    garbled reply -> concern/none, never a silent approve)."""
    t = str(raw or "")
    _v = re.search(r"VERDICT:\s*(approve|concern|block)", t, re.I)
    _s = re.search(r"SEVERITY:\s*(P0|P1|P2|P3|none)", t, re.I)
    _n = re.search(r"NOTE:\s*(.+)", t)
    verdict = (_v.group(1).lower() if _v else "concern")
    sev = (_s.group(1).upper() if _s else "NONE")
    note = (_n.group(1).strip()[:400] if _n else t.strip()[:200])
    return {"verdict": verdict, "severity": sev, "note": note}


def blocks(verdict):
    """Does this verdict block the review gate (#51)? A P0/P1 'block' from a can_block role halts."""
    return verdict.get("verdict") == "block" and verdict.get("severity") in ("P0", "P1")


def update_memory(memory, role_key, stage, verdict):
    """Append this engagement to the role's evolving memory (what it has already judged — so it defends the
    project across stages instead of re-deriving it)."""
    line = "[%s @ %s] %s (%s): %s" % (role_key, stage, verdict.get("verdict"), verdict.get("severity"),
                                      verdict.get("note", ""))
    return ((memory + "\n") if memory else "") + line


def engage(role_key, stage, artifact, charter, memory="", analyst_fn=None):
    """Engage a standing role at `stage` on `artifact`. Uses its SOUL + the charter + its memory. `analyst_fn`
    is the frontier callable (injected); without it, returns a skipped verdict (never raises). Returns
    (verdict_dict, new_memory)."""
    if role_key not in _BY_KEY:
        return {"verdict": "concern", "severity": "NONE", "note": "unknown role %r" % role_key}, memory
    if analyst_fn is None:
        v = {"verdict": "concern", "severity": "NONE", "note": "standing role not engaged (no analyst)"}
        return v, memory
    try:
        raw = analyst_fn(_prompt(role_key, stage, artifact, charter or {}, memory)) or ""
        v = parse_verdict(raw)
    except Exception as e:
        v = {"verdict": "concern", "severity": "NONE", "note": "engage error: %s" % type(e).__name__}
    return v, update_memory(memory, role_key, stage, v)
