"""spec_test_consistency_gate.py — proof that we catch a spec that contradicts its own acceptance test.

Reproduces the real 2026-07-08 helicopter failure: a spec with a "no obstacles for the FIRST 5 SECONDS" grace
period + a "hold Space 1.2s -> #score increases" test = a working build scores 0 and fails. The check MUST
flag it (rule score-vs-grace), MUST flag a test asserting on an element the spec never creates (selector-
undeclared), and MUST stay quiet on a consistent spec. So this class can't recur silently.
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
import spec_test_consistency as stc   # noqa: E402


def main():
    problems = []

    # 1) the exact helicopter contradiction MUST be flagged (score-vs-grace).
    heli_spec = ("Retro helicopter dodging game. For the FIRST 5 SECONDS of every run the screen has NO "
                 "obstacles at all. Below the canvas place <span id='score'></span> showing the score.")
    heli_behavior = [{"hold": "Space", "ms": 900, "expect": "up"},
                     {"idle": 900, "expect": "down"},
                     {"hold": "Space", "ms": 1200, "state": {"selector": "#score", "op": "increases"}}]
    w = stc.check(heli_spec, heli_behavior)
    if not any(x["rule"] == "score-vs-grace" for x in w):
        problems.append("did NOT flag the score-vs-grace contradiction: %r" % w)

    # 2) a test asserting on an undeclared element MUST be flagged.
    w2 = stc.check("A simple canvas game with a helicopter.", [{"idle": 500, "state": {"selector": "#health", "op": "changes"}}])
    if not any(x["rule"] == "selector-undeclared" for x in w2):
        problems.append("did NOT flag an undeclared selector: %r" % w2)

    # 3) a CONSISTENT spec must stay quiet: score element declared, no grace period, motion trials only.
    good_spec = "A helicopter game. Holding Space thrusts up; releasing falls. Shows <div id='score'>0</div>."
    good_behavior = [{"hold": "Space", "ms": 900, "expect": "up"},
                     {"press": "Space", "ms": 300, "state": {"selector": "#score", "op": "increases"}}]
    w3 = stc.check(good_spec, good_behavior)
    if w3:
        problems.append("false positive on a consistent spec: %r" % w3)

    # 4) a score test with a window LONGER than the grace period is fine (no false flag).
    w4 = stc.check(heli_spec, [{"hold": "Space", "ms": 7000, "state": {"selector": "#score", "op": "increases"}}])
    if any(x["rule"] == "score-vs-grace" for x in w4):
        problems.append("flagged score-vs-grace even though the window exceeds the grace period: %r" % w4)

    # 5) never raises on junk.
    try:
        stc.check(None, None); stc.check("", [{"weird": 1}, "notadict"])
    except Exception as e:
        problems.append("check raised on junk input: %s" % e)

    if problems:
        print("spec-test-consistency gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("spec-test-consistency gate: PASS — catches score-vs-grace + undeclared-selector contradictions, "
          "stays quiet on a consistent spec, no false flag on a long-enough window, never raises")
    sys.exit(0)


if __name__ == "__main__":
    main()
