"""intake_confirm_gate.py — MASTER_PLAN A3/A4 proof: per-assumption confirm + spec approval behave correctly.

Drives tools/intake_confirm.py with SCRIPTED responders (no stdin) and asserts: accept keeps as accepted, a
drop token removes an assumption, replacement text edits it, and spec approval maps ""/yes -> approved,
no -> rejected, other text -> revision. So the interactive intake's decision logic can't silently regress.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import intake_confirm as ic   # noqa: E402


def main():
    problems = []
    A = [{"text": "controls: hold Space to rise", "materiality": "high", "category": "controls"},
         {"text": "background is dark", "materiality": "low", "category": "visual"},
         {"text": "score shown top-left", "materiality": "med", "category": "ui"}]

    # A3.1 accept all -> all kept, tagged accepted.
    kept = ic.confirm_assumptions(A, lambda a: "")
    if len(kept) != 3 or any(k["confirmed"] != "accepted" for k in kept):
        problems.append("accept-all did not keep+tag all as accepted: %r" % kept)

    # A3.2 drop the middle -> 2 kept, the dropped one gone.
    kept = ic.confirm_assumptions(A, lambda a: "drop" if a["category"] == "visual" else "")
    if len(kept) != 2 or any(k["category"] == "visual" for k in kept):
        problems.append("drop token did not remove the assumption: %r" % kept)

    # A3.3 edit one -> text replaced, tagged edited, inputs not mutated.
    kept = ic.confirm_assumptions(A, lambda a: "hold ArrowUp to rise" if a["category"] == "controls" else "")
    ctrl = [k for k in kept if k["category"] == "controls"]
    if not ctrl or ctrl[0]["text"] != "hold ArrowUp to rise" or ctrl[0]["confirmed"] != "edited":
        problems.append("edit did not replace+tag: %r" % kept)
    if A[0]["text"] != "controls: hold Space to rise":
        problems.append("confirm_assumptions mutated its input")

    # A4 approve/reject/revise.
    if ic.approve_spec("SPEC", lambda s: "") != (True, None):
        problems.append("empty reply should approve")
    if ic.approve_spec("SPEC", lambda s: "yes") != (True, None):
        problems.append("'yes' should approve")
    if ic.approve_spec("SPEC", lambda s: "no") != (False, None):
        problems.append("'no' should reject")
    ap, rev = ic.approve_spec("SPEC", lambda s: "make the helicopter bigger")
    if ap is not False or rev != "make the helicopter bigger":
        problems.append("free text should be a revision request: %r" % ((ap, rev),))

    if problems:
        print("intake-confirm gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("intake-confirm gate: PASS — per-assumption accept/drop/edit + spec approve/reject/revise all correct")
    sys.exit(0)


if __name__ == "__main__":
    main()
