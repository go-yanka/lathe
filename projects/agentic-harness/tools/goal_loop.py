"""A2 — the goal loop (autonomy). Drives a bounded build step until a JUDGE says the goal is met.

Ported pattern from a prior agent `a prior agent_cli/goals.py`, with the key inversion proven tonight:
the judge is CLAUDE (reliable, free via the :8787 proxy), not the local 26B (which can't
self-judge). The build step is bounded + GATED (in A3 it's `hrun.py`), so the 26B only fills
tiny verified regions — autonomy with a quality bar, never free-handing.

Verdicts: done | escalate (needs a human) | paused (budget exhausted).

Anti-thrash (Rule of Three, from the gap analysis): if the build step makes NO progress for
3 turns running, escalate instead of looping — the deterministic cure for the spinning the
26B did tonight. A judge-driven loop without this can spin forever.
"""
import json
import re
import urllib.request

ESCALATE_MARKERS = ("NEEDS-YOU", "BLOCKED:", "HUMAN REVIEW", "DECISION_REQUIRED")


def claude_judge(goal, last_result, proxy_url="http://127.0.0.1:8787/v1/chat/completions",
                 model="sonnet", timeout=120):
    """OPT-IN judge — calls Claude via the :8787 proxy (`claude -p`).

    ⚠ OFF BY DEFAULT. `claude -p` runs on the SAME Max-subscription as the orchestrator
    session, so each call burns the same usage limits — a looping agent calling this would
    hit the rate caps fast. Per the binding cost principle (no programmatic Claude calls),
    the default judge is `gate_judge` (deterministic), and fuzzy judgments are handed to the
    orchestrator session IN-BAND. Use this only if you actually have API/limit budget to spend.

    Returns (done, reason). Fail-OPEN if the proxy is unreachable."""
    sys_p = ("You are a strict judge for an autonomous build loop. Given a GOAL and the latest "
             "BUILD RESULT (gate output), decide if the goal is FULLY met. Reply with ONLY a JSON "
             'object: {"done": true|false, "reason": "<one line>"}.')
    user_p = f"GOAL:\n{goal}\n\nLATEST BUILD RESULT:\n{(last_result or '')[:4000]}\n\nIs the goal fully met?"
    body = json.dumps({"model": model, "stream": False, "messages": [
        {"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]}).encode("utf-8")
    try:
        req = urllib.request.Request(proxy_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = json.loads(r.read().decode("utf-8", "replace"))["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.S)
        d = json.loads(m.group(0)) if m else {}
        return bool(d.get("done", False)), str(d.get("reason", ""))[:200]
    except Exception as e:
        return False, f"judge unreachable: {e}"


def gate_judge(goal, last_result):
    """DEFAULT judge — DETERMINISTIC, makes ZERO Claude calls (the binding cost rule:
    a programmatic Claude call burns the same Max-sub limits as the orchestrator session).
    'gates green' => goal met. FUZZY judgments (design quality, spec intent, hard debugging)
    are NOT decided here — the loop escalates them to the orchestrator session, which answers
    IN-BAND (the conversation already happening), adding no extra Claude usage.

    Structured path: when the result is a real engine RUN_REPORT ('functions implemented: N/M'),
    it reads it with the harness's OWN gate_report parser (built by this harness, plan A4a) — a
    SKIPPED/absent integration test does not block green; only an explicit FAIL does. Otherwise
    it falls back to loose green/fail markers."""
    rl = last_result or ""
    low = rl.lower()
    # Structured path — a genuine engine RUN_REPORT. Dogfoods our own parser (A4a).
    try:
        from gate_report import parse_run_report, is_green
        rep = parse_run_report(rl)
        if rep.get("functions_total", 0) > 0:
            tag = f"{rep['functions_passed']}/{rep['functions_total']}, integration={rep['integration_status']}"
            return (True, f"gates green ({tag})") if is_green(rep) else (False, f"not green ({tag})")
    except Exception:
        pass
    # Loose-marker fallback — no structured report present.
    green = any(k in low for k in ("gates green", "integration: pass", "all assertions pass", "gate: pass"))
    failed = (any(k in low for k in ("integration: fail", "gate: fail", "gates failed"))
              or ("fail" in low and "pass" not in low))
    if green and not failed:
        return True, "gates green (deterministic)"
    return False, "gates not green"


def run_goal_loop(goal, build_step, judge=gate_judge, max_turns=20, on_event=None):
    """Drive build_step(turn, last_result) -> result_str until the judge says done.

    build_step: a callable doing ONE bounded, gated build attempt; returns a result string
                (in A3, this runs a plan through hrun.py and returns the gate output).
    judge:      (goal, result) -> (done: bool, reason: str). Defaults to claude_judge.
    Returns {"outcome": done|escalate|paused, "turns": int, "reason": str}.
    """
    def emit(m):
        if on_event:
            on_event(m)

    last_result = None
    repeat = 0
    for turn in range(1, max_turns + 1):
        result = build_step(turn, last_result) or ""
        emit(f"turn {turn}: {result[:80]}")

        # 1) explicit escalation — the step needs a human decision
        if any(mk in result for mk in ESCALATE_MARKERS):
            return {"outcome": "escalate", "turns": turn, "reason": result[:200]}

        # 2) anti-thrash (Rule of Three): 3 identical results in a row = stuck
        repeat = repeat + 1 if result == last_result else 0
        if repeat >= 2:
            return {"outcome": "escalate", "turns": turn,
                    "reason": "no progress for 3 turns (stuck) — needs human/redirect"}
        last_result = result

        # 3) is the goal met?
        done, reason = judge(goal, result)
        if done:
            return {"outcome": "done", "turns": turn, "reason": reason}

    return {"outcome": "paused", "turns": max_turns, "reason": "turn budget exhausted"}
