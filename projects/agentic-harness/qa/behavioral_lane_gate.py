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

# The spec that separates a real helicopter from a dead one.
SPEC = [
    {"hold": "Space", "ms": 900, "expect": "up"},    # thrust must lift the craft
    {"idle": 900, "expect": "down"},                 # with no input, gravity must pull it down
]


def _run(fixture):
    """Run the compiled behavioral gate against a fixture. Return (returncode, tail_of_output)."""
    script = bg.build_script(SPEC)
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

    good_rc, good_tail = _run("heli_good.html")
    bad_rc, bad_tail = _run("heli_bad.html")

    problems = []
    if good_rc != 0:
        problems.append("heli_good MUST pass but FAILED: %s" % good_tail)
    if bad_rc == 0:
        problems.append("heli_bad MUST fail (dead control) but PASSED — interpreter is not discriminating")

    if problems:
        print("behavioral-lane gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)

    print("behavioral-lane gate: PASS — working helicopter passes, dead-control helicopter fails "
          "(input->response is enforced, not just liveness)")
    sys.exit(0)


if __name__ == "__main__":
    main()
