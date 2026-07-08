"""behavioral_lane_gate.py — MASTER_PLAN D1 proof: the behavioral interpreter DISCRIMINATES play from liveness.

This standing gate proves `tools/behavioral_gate.py` actually closes the helicopter class. It compiles ONE
behavioral spec (hold Space -> the craft should RISE; idle -> it should FALL) and runs it against two fixtures:

  - heli_good.html : Space thrusts the craft up      -> MUST PASS the spec
  - heli_bad.html  : Space is inert, gravity only    -> MUST FAIL the spec (its `hold Space expect up` trial)

Both fixtures ANIMATE, so the old liveness gate (web_canvas_game) passes BOTH — that is exactly the blind spot.
If good does not pass, or bad does not fail, the interpreter is broken and this gate FAILS loudly. That is the
standing proof required by the meta-rule (a wire is DONE only when a gate proves it).

Needs Playwright/Chromium (same stack the web build gates already use). If it cannot launch, the gate reports
INOPERATIVE and fails closed — never a silent pass.
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import subprocess
import sys
import tempfile

QA = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(QA), "tools")
FIX = os.path.join(QA, "fixtures")
sys.path.insert(0, TOOLS)

import behavioral_gate as bg   # noqa: E402
import func_gates as fg         # noqa: E402

# D1 — the motion spec that separates a real helicopter from a dead one.
HELI_SPEC = [
    {"hold": "Space", "ms": 900, "expect": "up"},    # thrust must lift the craft
    {"idle": 900, "expect": "down"},                 # with no input, gravity must pull it down
]
# D2 — the STATE spec that separates a real scorer from a frozen-score one (pressing Space must score).
SCORE_SPEC = [
    {"press": "Space", "ms": 200, "state": {"selector": "#score", "op": "increases"}},
]

# Each proof: (spec, good_fixture, bad_fixture). good MUST pass; bad MUST fail.
PROOFS = [
    ("D1 motion (helicopter)", HELI_SPEC, "heli_good.html", "heli_bad.html"),
    ("D2 state (score)", SCORE_SPEC, "score_good.html", "score_bad.html"),
]


def _run_src(script, fixture):
    """Run a gate SCRIPT (source string) against a fixture. Return (returncode, tail_of_output)."""
    env = dict(os.environ)
    env["ARTIFACT_FILE"] = os.path.join(FIX, fixture)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as th:
        th.write(script); sp = th.name
    try:
        r = subprocess.run([sys.executable, sp], capture_output=True, text=True, env=env,
                           encoding="utf-8", errors="replace", timeout=90)
    finally:
        try:
            os.unlink(sp)
        except OSError:
            pass
    out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    return r.returncode, (out[-1] if out else "")[:180]


def main():
    # fail-closed availability probe: a gate that can't run is INOPERATIVE, not a silent pass.
    try:
        import playwright  # noqa: F401
    except Exception as e:
        print("behavioral-lane gate: INOPERATIVE — Playwright unavailable: %s" % e)
        sys.exit(1)

    problems = []
    # D1/D2 interpreter proofs: analyst-authored specs discriminate working builds from broken ones.
    for name, spec, good_fx, bad_fx in PROOFS:
        good_rc, good_tail = _run_src(bg.build_script(spec), good_fx)
        bad_rc, bad_tail = _run_src(bg.build_script(spec), bad_fx)
        if good_rc != 0:
            problems.append("%s: %s MUST pass but FAILED: %s" % (name, good_fx, good_tail))
        if bad_rc == 0:
            problems.append("%s: %s MUST fail but PASSED — interpreter is not discriminating" % (name, bad_fx))

    # D2 default-lane proof: even with NO analyst spec, web_canvas_game rejects an instant-game-over build.
    wcg = fg.resolve("web_canvas_game")
    g_rc, _ = _run_src(wcg, "heli_good.html")            # animating, playable -> PASS
    b_rc, b_tail = _run_src(wcg, "gameover_bad.html")    # dies as soon as it starts -> FAIL
    if g_rc != 0:
        problems.append("D2 default (web_canvas_game): heli_good MUST pass but FAILED")
    if b_rc == 0:
        problems.append("D2 default (web_canvas_game): gameover_bad MUST fail (instant game-over) but PASSED")

    if problems:
        print("behavioral-lane gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)

    print("behavioral-lane gate: PASS — %d interpreter proof(s) + web_canvas_game instant-game-over guard: "
          "working builds pass, broken ones fail (motion + state + not-instant-death enforced, not just "
          "liveness)" % len(PROOFS))
    sys.exit(0)


if __name__ == "__main__":
    main()
