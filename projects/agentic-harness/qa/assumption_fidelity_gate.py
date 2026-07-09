"""assumption_fidelity_gate.py — prove the input-purity check works: a confirmed choice that got DROPPED from
the build is flagged; choices that ARE reflected (even reworded) pass; empty/degenerate inputs never raise."""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import assumption_fidelity as af   # noqa: E402


def main():
    problems = []

    confirmed = [
        "Snake collides with a wall ends the game",
        "Pressing the opposite arrow (180 reversal) is ignored",
        "Food spawns on a random empty cell",
        "High score persists across sessions via localStorage",     # <- this one will be DROPPED from the spec
    ]
    # a drafted spec that HONOURS the first three (reworded) but never mentions persistence/localStorage
    spec = ("The snake dies and the game ends when it hits a wall. An arrow key opposite to the current travel "
            "direction is rejected (no 180 reversal). Food appears at a uniformly random empty cell.")

    missing = af.unhonored(confirmed, spec)
    miss_txt = [m["assumption"] for m in missing]
    if not any("localStorage" in m for m in miss_txt):
        problems.append("did NOT flag the dropped localStorage choice: %r" % missing)
    if any("wall" in m or "reversal" in m or "random empty" in m for m in miss_txt):
        problems.append("false-positive: flagged a choice that IS reflected (reworded): %r" % missing)

    # all-reflected -> empty result
    if af.unhonored(["hits a wall ends the game"], "the game ends when the snake hits a wall"):
        problems.append("flagged a fully-reflected choice")

    # degenerate inputs never raise, return empty
    for c, d in (([], "x"), (None, None), (["   "], ""), ([{"text": ""}], "y")):
        try:
            if af.unhonored(c, d):
                problems.append("spurious flag on degenerate input %r/%r" % (c, d))
        except Exception as e:
            problems.append("raised on degenerate input %r: %s" % (c, e))

    # dict form works too
    if not af.unhonored([{"text": "localStorage high score persistence"}], "a plain snake with no storage"):
        problems.append("dict-form assumption not checked")

    # summary is a plain string
    if not isinstance(af.summary(missing, len(confirmed)), str):
        problems.append("summary not a string")

    if problems:
        print("assumption-fidelity gate: FAIL — " + " ;; ".join(problems)); sys.exit(1)
    print("assumption-fidelity gate: PASS — dropped confirmed choices are flagged, reflected/reworded ones pass, "
          "degenerate inputs never raise")
    sys.exit(0)


if __name__ == "__main__":
    main()
