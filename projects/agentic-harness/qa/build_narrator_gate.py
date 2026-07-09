"""build_narrator_gate.py — proof the human-interpretation layer reads the engine output correctly for EVERY
build path (all workflows now route through engine_runner -> build_narrator).

Feeds synthetic engine outputs and asserts the plain-English summary reports: SUCCESS vs NOTHING SHIPPED,
loop #1 / loop #2 firings, per-attempt reasons translated to layman ("held the control, it fell"; "crashed"),
an INOPERATIVE environment failure (not blamed on the spec), and that it never raises.
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
import build_narrator as bn   # noqa: E402

_OK = ('===METRICS_JSON_BEGIN=== {"build_ok": true, "functions_total": 1, "functions_passed": 1, '
       '"artifacts_total": 0, "artifacts_passed": 0, "pins_added": 1, "elapsed_s": 3} ===METRICS_JSON_END===')

_FAIL = (
    "  [spec<->test WARNING] motion-vs-paused\n"
    "  [spec<->test REFINED] contradiction resolved BEFORE the implementer (rounds=1)\n"
    "    [targeted repair] attempt 2: fixing the exact failure from attempt 1\n"
    "    [attempt 1 FAILED - why: BEHAVIORAL FAIL: hold Space -> expected foreground to move UP (dy=143.8)]\n"
    "    [attempt 2 FAILED - why: JS error: Cannot read properties of undefined (reading 'hasMid')]\n"
    '===METRICS_JSON_BEGIN=== {"build_ok": false, "artifacts_total": 1, "artifacts_passed": 0, "elapsed_s": 275} ===METRICS_JSON_END===')

_INOP = "  [artifact GATE INOPERATIVE (environment)] browser missing"


def main():
    problems = []

    ok = bn.interpret(_OK, "do build")
    if "SUCCESS" not in ok or "1/1 function" not in ok:
        problems.append("success not reported: %r" % ok)
    if "pinned) 1" not in ok:
        problems.append("pins not reported on success")

    f = bn.interpret(_FAIL)
    if "NOTHING SHIPPED" not in f:
        problems.append("failure verdict not reported")
    if "loop #1" not in f or "fixed 1" not in f:
        problems.append("loop #1 firing not reported: %r" % f)
    if "loop #2" not in f or "fired 1" not in f:
        problems.append("loop #2 firing not reported")
    if "did NOT lift" not in f and "fell instead" not in f:
        problems.append("attempt-1 physics failure not translated to layman: %r" % f)
    if "CRASHED" not in f:
        problems.append("attempt-2 JS crash not translated to layman")
    if "WHAT TO DO" not in f:
        problems.append("no advice on failure")

    inop = bn.interpret(_INOP)
    if "COULD NOT JUDGE" not in inop or "NOT a spec failure" not in inop:
        problems.append("inoperative env not handled as non-spec-failure: %r" % inop)

    # never raises on junk / empty
    try:
        bn.interpret(None); bn.interpret(""); bn.interpret("garbage no json")
    except Exception as e:
        problems.append("interpret raised on junk: %s" % e)

    if problems:
        print("build-narrator gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("build-narrator gate: PASS — plain-English layer reports success/failure, loop #1/#2 firings, "
          "layman per-attempt reasons, inoperative-env (not spec's fault), and never raises")
    sys.exit(0)


if __name__ == "__main__":
    main()
