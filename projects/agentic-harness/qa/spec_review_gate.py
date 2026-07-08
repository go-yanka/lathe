"""spec_review_gate.py — proof the closed loop CONVERGES: a contradictory spec is refined to clean before the
implementer, and a clean spec is left untouched.

Drives tools/spec_review.py with a STUB analyst (no model). The stub's `refine` fixes the score-vs-grace
contradiction (widens the score-check window past the grace period). The gate asserts: converge() reaches
`clean` on the helicopter contradiction within max_rounds; an already-clean spec returns at round 0 with no
refinement; a stubborn analyst that never fixes it ends `clean=False` (surfaced, not hidden); never raises.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(QA), "tools"))
import spec_review as sr   # noqa: E402

HELI_SPEC = ("Retro helicopter game. For the FIRST 5 SECONDS of every run there are NO obstacles. "
             "Below the canvas place <span id='score'></span>.")
HELI_BEHAVIOR = [{"hold": "Space", "ms": 900, "expect": "up"},
                 {"hold": "Space", "ms": 1200, "state": {"selector": "#score", "op": "increases"}}]


def _fixing_analyst(prompt, model=None):
    # critique -> report the contradiction; refine -> widen the score window past the 5s grace so it's fair.
    if "Reply with ONLY compact JSON" in prompt:   # the refine prompt
        fixed = [{"hold": "Space", "ms": 900, "expect": "up"},
                 {"hold": "Space", "ms": 7000, "state": {"selector": "#score", "op": "increases"}}]
        return json.dumps({"spec": HELI_SPEC, "behavior": fixed})
    return "the score test window is inside the 5s grace period"   # critique


def _stubborn_analyst(prompt, model=None):
    if "Reply with ONLY compact JSON" in prompt:
        return json.dumps({"spec": HELI_SPEC, "behavior": HELI_BEHAVIOR})   # never fixes it
    return "NONE"


def main():
    problems = []

    # 1) contradiction -> converge to clean within max_rounds, and the returned behavior is the fixed one.
    r = sr.converge(HELI_SPEC, HELI_BEHAVIOR, analyst_fn=_fixing_analyst, max_rounds=2)
    if not r["clean"]:
        problems.append("did not converge to clean on the helicopter contradiction: %r" % r["history"])
    if r["rounds"] < 1:
        problems.append("claimed clean without refining a known contradiction")
    if sr.deterministic_problems(r["spec"], r["behavior"]):
        problems.append("returned spec still fails the deterministic bar")

    # 2) an already-clean spec: no refinement, round 0.
    clean_spec = "A helicopter game. Hold Space to rise. Shows <div id='score'>0</div>."
    clean_beh = [{"hold": "Space", "ms": 900, "expect": "up"}]
    r2 = sr.converge(clean_spec, clean_beh, analyst_fn=_fixing_analyst, max_rounds=2)
    if not r2["clean"] or r2["rounds"] != 0:
        problems.append("a clean spec should return clean at round 0: %r" % {k: r2[k] for k in ("clean", "rounds")})

    # 3) a stubborn analyst -> ends clean=False (surfaced), does not loop forever or claim success.
    r3 = sr.converge(HELI_SPEC, HELI_BEHAVIOR, analyst_fn=_stubborn_analyst, max_rounds=2)
    if r3["clean"]:
        problems.append("claimed clean when the analyst never fixed the contradiction")
    if r3["rounds"] != 2:
        problems.append("stubborn case should exhaust max_rounds: %r" % r3["rounds"])

    # 4) never raises on a dead analyst.
    def _boom(p, model=None):
        raise RuntimeError("down")
    try:
        sr.converge(HELI_SPEC, HELI_BEHAVIOR, analyst_fn=_boom, max_rounds=1)
    except Exception as e:
        problems.append("converge raised on a dead analyst: %s" % e)

    if problems:
        print("spec-review gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("spec-review gate: PASS — the loop converges a contradictory spec to clean before the implementer, "
          "leaves a clean spec untouched, surfaces an unfixable one (clean=False), and never raises")
    sys.exit(0)


if __name__ == "__main__":
    main()
