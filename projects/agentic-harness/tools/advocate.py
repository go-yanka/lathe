"""advocate.py — THE ADVOCATE: the sponsor's standing representative for the WHOLE run (default-on).

Unlike every other persona (stateless, one stage, then gone), the Advocate is seeded with the sponsor's intent
up front and stays for the entire run. It holds a CHARTER (goal + discovery answers + confirmed choices), and
at each checkpoint it judges ONE thing — does the work still serve the sponsor's INTENT, DIRECTION, and
QUALITY? — with authority to APPROVE, raise a CONCERN, or VETO and route the work back. It is the structural
answer to the failure that plagues agent systems: confidently shipping the wrong thing because "the build
finished". Loyalty is to intent, never to completion.

Driven by the `advocate` persona + the SSRF-guarded analyst client; pure/injectable so a gate proves the
verdict logic deterministically. Never raises — a broken Advocate call degrades to a recorded CONCERN, never a
silent pass and never a crash.
"""

import json
import os
import re

VERDICTS = ("approve", "concern", "veto")
ROUTES = ("", "rediscover", "reassume", "redraft", "rebuild")


def _persona():
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ce_personas", "advocate.md")
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    except Exception:
        return ""


def build_charter(goal, augmented_goal="", assumptions=None):
    """Assemble the sponsor's intent record the Advocate will hold. The augmented goal already carries the
    discovery + resolved-assumption blocks; we surface them as the charter."""
    parts = ["# ADVOCATE CHARTER — I represent the sponsor; this is their intent.", "", "## Goal", (goal or "").strip(), ""]
    aug = augmented_goal or ""
    if "WHAT THE USER ACTUALLY WANTS" in aug:               # the discovery answers = the real intent
        _d = aug.split("WHAT THE USER ACTUALLY WANTS", 1)[1].split("RESOLVED ASSUMPTIONS")[0].strip()
        parts += ["## Discovery — the real intent (why/who/success)", _d, ""]
    if assumptions:
        parts += ["## Confirmed choices (the sponsor approved these)"]
        parts += ["- [%s] %s" % ((a.get("materiality") or "").upper(), a.get("text", "")) for a in assumptions]
        parts += [""]
    return "\n".join(parts)


def _default_analyst():
    def _f(prompt, model=None):
        import request_spec
        return request_spec.request_spec(prompt, model=model or os.environ.get("LATHE_ADVOCATE_MODEL", "sonnet"),
                                         timeout=int(os.environ.get("LATHE_ADVOCATE_TIMEOUT", "90")))
    return _f


_PROMPT = (
    "{persona}\n\n=== YOUR CHARTER (the sponsor's intent — judge everything against this) ===\n{charter}\n\n"
    "=== CHECKPOINT: {stage} ===\n{context}\n\nHere is what was produced / is about to happen:\n---\n{artifact}\n---\n\n"
    "Judge ONLY whether this still serves the sponsor's intent, direction, and quality (NOT code correctness). "
    "Reply with ONLY compact JSON, nothing else:\n"
    '{{"verdict": "approve|concern|veto", "note": "<specific — quote the intent it serves or violates>", '
    '"route": "|rediscover|reassume|redraft|rebuild"}}'
)


def checkpoint(charter, stage, artifact_summary, context="", analyst_fn=None, model=None, persona=None):
    """Consult the Advocate at a stage boundary. Returns {verdict, note, route}. Never raises. On any failure
    (analyst down, unparseable) returns a CONCERN (surfaced, never a silent pass)."""
    analyst_fn = analyst_fn or _default_analyst()
    _p = persona if persona is not None else _persona()
    prompt = _PROMPT.format(persona=_p, charter=(charter or "")[:6000], stage=stage,
                            context=(context or ""), artifact=(artifact_summary or "")[:12000])
    try:
        reply = analyst_fn(prompt, model=model)
    except Exception as e:
        return {"verdict": "concern", "note": "advocate could not run (%s) — proceeding, but unwatched" % str(e)[:100], "route": ""}
    m = re.search(r"\{.*\}", reply or "", re.DOTALL)
    if not m:
        return {"verdict": "concern", "note": "advocate gave no parseable verdict", "route": ""}
    try:
        d = json.loads(m.group())
    except Exception:
        return {"verdict": "concern", "note": "advocate verdict unparseable", "route": ""}
    v = str(d.get("verdict", "")).strip().lower()
    if v not in VERDICTS:
        v = "concern"
    r = str(d.get("route", "")).strip().lower()
    if r not in ROUTES:
        r = ""
    return {"verdict": v, "note": str(d.get("note", ""))[:400], "route": r}


def render(verdict):
    """One-line human rendering of a verdict for the terminal. ASCII only — a Unicode glyph crashes a Windows
    cp1252 terminal (would kill the run when the verdict prints)."""
    _icon = {"approve": "[ADVOCATE: APPROVE]", "concern": "[ADVOCATE: CONCERN]", "veto": "[ADVOCATE: VETO]"}
    line = "%s %s" % (_icon.get(verdict.get("verdict"), "[ADVOCATE]"), verdict.get("note", ""))
    if verdict.get("verdict") == "veto" and verdict.get("route"):
        line += "  → route: %s" % verdict["route"]
    return line
