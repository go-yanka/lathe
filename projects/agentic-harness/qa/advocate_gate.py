"""advocate_gate.py — proof the Advocate's charter + verdict logic is correct and fail-safe.

Deterministic (stub analyst): charter assembly carries the sponsor's intent; a stub verdict maps approve/
concern/veto; an unknown verdict degrades to CONCERN; an analyst outage degrades to CONCERN (never a silent
pass, never a crash); render() labels each. The LIVE intent-judgment (approve aligned / veto misaligned) is
non-deterministic and validated on demand.
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
import advocate as adv   # noqa: E402


def main():
    problems = []

    # charter carries the intent
    ch = adv.build_charter("a retro helicopter game",
                           "goal\n\nWHAT THE USER ACTUALLY WANTS (from discovery):\n- Q: who for? A: nostalgia\nRESOLVED ASSUMPTIONS",
                           [{"materiality": "high", "text": "hold Space to rise"}])
    if "sponsor" not in ch.lower() or "nostalgia" not in ch or "hold Space to rise" not in ch:
        problems.append("charter missing intent/discovery/choices: %r" % ch[:200])

    # stub verdicts map through, with persona injected empty (no file read needed)
    v = adv.checkpoint("charter", "delivery", "<the built thing>", persona="",
                       analyst_fn=lambda p, model=None: '{"verdict":"approve","note":"matches intent","route":""}')
    if v["verdict"] != "approve":
        problems.append("approve not mapped: %r" % v)
    v = adv.checkpoint("charter", "delivery", "<off-topic thing>", persona="",
                       analyst_fn=lambda p, model=None: '{"verdict":"veto","note":"not what they asked","route":"redraft"}')
    if v["verdict"] != "veto" or v["route"] != "redraft":
        problems.append("veto+route not mapped: %r" % v)

    # unknown verdict -> concern; unknown route -> ""
    v = adv.checkpoint("c", "s", "a", persona="", analyst_fn=lambda p, model=None: '{"verdict":"lgtm","route":"nowhere"}')
    if v["verdict"] != "concern" or v["route"] != "":
        problems.append("unknown verdict/route not sanitized: %r" % v)

    # analyst outage / garbage -> concern, never raises
    def _boom(p, model=None):
        raise RuntimeError("down")
    try:
        v = adv.checkpoint("c", "s", "a", persona="", analyst_fn=_boom)
    except Exception as e:
        problems.append("a raising analyst propagated: %s" % e); v = {}
    if v.get("verdict") != "concern":
        problems.append("analyst outage not mapped to concern: %r" % v)
    if adv.checkpoint("c", "s", "a", persona="", analyst_fn=lambda p, model=None: "no json")["verdict"] != "concern":
        problems.append("garbage reply not mapped to concern")

    # render labels
    if "VETO" not in adv.render({"verdict": "veto", "note": "x", "route": "redraft"}):
        problems.append("render missing VETO label")

    if problems:
        print("advocate gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("advocate gate: PASS — charter carries intent; approve/concern/veto map; unknowns + outages degrade "
          "to CONCERN (never silent pass, never crash); render labels verdicts")
    sys.exit(0)


if __name__ == "__main__":
    main()
