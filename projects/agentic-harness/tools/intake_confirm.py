"""intake_confirm.py — MASTER_PLAN A3/A4: per-assumption confirmation + spec approval (pure, testable).

The interactive intake needs to let the user confirm/correct EACH surfaced assumption (A3) and approve the
refined spec before a build starts (A4). The I/O (input()) is not testable, so the DECISION logic lives here as
pure functions driven by an injected `responder` callable. lathe.py passes a real input()-backed responder;
qa/intake_confirm_gate.py passes a scripted one — so the confirm/approve behaviour is provable with no stdin.
"""

_ACCEPT = ("", "y", "yes", "ok", "accept", "keep")
_DROP = ("d", "drop", "n", "no", "-", "remove")
_APPROVE = ("", "y", "yes", "ok", "approve", "g", "go", "lgtm")
_REJECT = ("n", "no", "abort", "cancel", "stop", "q", "quit")


def confirm_assumptions(assumptions, responder):
    """A3: walk each assumption; the responder returns "" (accept), a drop token, or replacement text.
    Returns a NEW list of the kept assumptions, each tagged with confirmed = accepted|edited (dropped ones are
    omitted). `responder(assumption_dict) -> str`. Never mutates the inputs."""
    kept = []
    for a in assumptions:
        try:
            r = (responder(a) or "").strip()
        except (EOFError, KeyboardInterrupt):
            r = ""                                   # treat an interrupted prompt as accept-remaining
        low = r.lower()
        if low in _DROP:
            continue
        b = dict(a)
        if r and low not in _ACCEPT:
            b["text"] = r
            b["category"] = b.get("category", "user")
            b["confirmed"] = "edited"
        else:
            b["confirmed"] = "accepted"
        kept.append(b)
    return kept


def approve_spec(summary, responder):
    """A4: show the refined spec summary; the responder returns approve/reject/revision.
    Returns (approved: bool, revision: str|None). A non-approve, non-reject reply is treated as a revision
    request (approved=False, revision=text). `responder(summary) -> str`."""
    try:
        r = (responder(summary) or "").strip()
    except (EOFError, KeyboardInterrupt):
        r = ""                                       # interrupted -> default approve (assume-and-record intent)
    low = r.lower()
    if low in _APPROVE:
        return True, None
    if low in _REJECT:
        return False, None
    return False, r
