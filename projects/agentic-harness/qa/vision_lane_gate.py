"""vision_lane_gate.py — MASTER_PLAN D3 proof: the visual-judge PLUMBING works and is fail-safe (advisory).

The LIVE model judgement is non-deterministic (proven on demand via vision_judge.judge_live — it passes real
renders and fails a blank page). This STANDING gate proves the deterministic wiring around it, with NO model
call, using a STUB judge:
  - capture() takes a real screenshot of a fixture (non-trivial PNG bytes);
  - judge() with a stub returning a good verdict -> "pass"; a bad verdict -> "fail";
  - a stub that RAISES -> "inoperative" (advisory: a broken judge NEVER breaks the build, never raises);
  - parse_verdict() handles JSON, prose, and garbage.
So the wire (screenshot -> encode -> judge -> parse -> advisory verdict) can never silently un-wire.

Needs Playwright for capture(); if unavailable the gate is INOPERATIVE (fails closed, never a silent pass).
"""
for _s in (__import__("sys").stdout, __import__("sys").stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import sys

QA = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(QA), "tools")
FIX = os.path.join(QA, "fixtures")
sys.path.insert(0, TOOLS)

import vision_judge as vj   # noqa: E402


def main():
    try:
        import playwright  # noqa: F401
    except Exception as e:
        print("vision-lane gate: INOPERATIVE — Playwright unavailable: %s" % e)
        sys.exit(1)

    problems = []

    # 1) capture() produces real, non-trivial PNG bytes for a rendered fixture.
    try:
        png = vj.capture(os.path.join(FIX, "heli_good.html"))
    except Exception as e:
        print("vision-lane gate: INOPERATIVE — capture failed: %s" % e); sys.exit(1)
    if not (isinstance(png, (bytes, bytearray)) and png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 1000):
        problems.append("capture did not return a non-trivial PNG (%d bytes)" % len(png or b""))

    # 2) a stub judge returning a GOOD verdict -> pass; a BAD verdict -> fail.
    good = vj.judge(bytes(png), "a canvas game",
                    judge_fn=lambda pr, uri: '{"looks_right": true, "confidence": 0.9, "issues": []}')
    if good.get("verdict") != "pass" or good.get("looks_right") is not True:
        problems.append("stub GOOD verdict not mapped to pass: %r" % good)
    bad = vj.judge(bytes(png), "a canvas game",
                   judge_fn=lambda pr, uri: '{"looks_right": false, "confidence": 0.95, "issues": ["blank"]}')
    if bad.get("verdict") != "fail" or bad.get("looks_right") is not False:
        problems.append("stub BAD verdict not mapped to fail: %r" % bad)

    # 3) a judge that RAISES must be advisory 'inoperative', never propagate.
    def _boom(pr, uri):
        raise RuntimeError("judge endpoint down")
    try:
        inop = vj.judge(bytes(png), "a canvas game", judge_fn=_boom)
    except Exception as e:
        problems.append("a raising judge propagated instead of being advisory: %s" % e)
        inop = {}
    if inop.get("verdict") != "inoperative":
        problems.append("raising judge not mapped to inoperative: %r" % inop)

    # 4) parse_verdict robustness: JSON, prose, garbage.
    if vj.parse_verdict('{"looks_right": true, "confidence": 0.8}') is None:
        problems.append("parse_verdict failed on clean JSON")
    if vj.parse_verdict("the page is completely blank and broken") is None:
        problems.append("parse_verdict failed on prose")
    if vj.parse_verdict("") is not None:
        problems.append("parse_verdict should return None on empty input")

    if problems:
        print("vision-lane gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)

    print("vision-lane gate: PASS — screenshot->judge->verdict pipeline works and is fail-safe advisory "
          "(good->pass, bad->fail, judge-down->inoperative, never raises); live model judging is opt-in")
    sys.exit(0)


if __name__ == "__main__":
    main()
