"""A2 tests — executable spec for the goal loop. Deterministic (stub judge, no live proxy).
Run: python tools/test_goal_loop.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from goal_loop import run_goal_loop, claude_judge


def main():
    # 1. SUCCESS: build fails twice, passes on turn 3; judge = "done when PASS"
    seq = ["gate: FAIL (1 test red)", "gate: FAIL (still red)", "gate: PASS 6/6"]
    judge_pass = lambda goal, res: ("PASS" in res, "gates green" if "PASS" in res else "not yet")
    r = run_goal_loop("make gates green", lambda t, last: seq[t - 1], judge=judge_pass, max_turns=10)
    assert r["outcome"] == "done" and r["turns"] == 3, f"success path wrong: {r}"

    # 2. ANTI-THRASH: build returns the SAME error forever; judge never done -> escalate at turn 3
    never = lambda goal, res: (False, "no")
    r = run_goal_loop("fix it", lambda t, last: "SAME ERROR: rom fastapi", judge=never, max_turns=20)
    assert r["outcome"] == "escalate" and r["turns"] == 3 and "no progress" in r["reason"], \
        f"anti-thrash should fire at turn 3, got: {r}"

    # 3. EXPLICIT ESCALATION: the step flags it needs a human -> escalate immediately
    r = run_goal_loop("build auth", lambda t, last: "STATUS: NEEDS-YOU: pick a session store", judge=never, max_turns=10)
    assert r["outcome"] == "escalate" and r["turns"] == 1, f"explicit escalation wrong: {r}"

    # 4. BUDGET: distinct non-passing results each turn (anti-thrash won't fire), judge never done -> paused
    r = run_goal_loop("hard goal", lambda t, last: f"gate: FAIL attempt {t}", judge=never, max_turns=5)
    assert r["outcome"] == "paused" and r["turns"] == 5, f"budget path wrong: {r}"

    # 5. events are emitted per turn
    events = []
    run_goal_loop("g", lambda t, last: ("PASS" if t == 2 else f"x{t}"), judge=judge_pass,
                  max_turns=5, on_event=events.append)
    assert len(events) == 2 and events[0].startswith("turn 1"), f"events wrong: {events}"

    # 6. claude_judge fails OPEN (never raises) when the proxy is unreachable
    done, reason = claude_judge("g", "r", proxy_url="http://127.0.0.1:59999/nope", timeout=2)
    assert done is False and "unreachable" in reason, f"judge should fail-open: {done}/{reason}"

    # 7. gate_judge is DETERMINISTIC (no Claude call) and is the DEFAULT
    import inspect
    from goal_loop import gate_judge, run_goal_loop as rgl
    assert gate_judge("g", "integration: PASS")[0] is True
    assert gate_judge("g", "GATES GREEN 6/6")[0] is True
    assert gate_judge("g", "integration: FAIL")[0] is False
    assert gate_judge("g", "still red")[0] is False
    assert inspect.signature(rgl).parameters["judge"].default is gate_judge, \
        "default judge must be deterministic gate_judge (no programmatic Claude calls)"

    print("A2 goal_loop: ALL 7 ASSERTIONS PASS — deterministic gate_judge DEFAULT (no Claude calls) + anti-thrash.")


if __name__ == "__main__":
    main()
