"""refute_lane_gate.py — MASTER_PLAN C1/C2 proof: the second-spec + refute PLUMBING works and is advisory.

The LIVE red-team is non-deterministic (proven on demand: the analyst enumerates concrete per-goal failure
hypotheses and refutes an artifact against them). This STANDING gate proves the deterministic wiring with a
STUB analyst — no model call:
  - hypotheses() parses the analyst's JSON array into normalized {id, hypothesis, check};
  - refute() maps per-hypothesis verdicts to {present[], verdict: holes|clean};
  - an analyst outage / garbage reply -> 'inoperative' (advisory), never a crash;
  - audit() composes the two.
So the wire (generate -> parse -> refute -> parse -> advisory report) can never silently un-wire.
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
sys.path.insert(0, TOOLS)

import refute_auditor as ra   # noqa: E402

_HYPS_JSON = ('[{"id":"dead-control","hypothesis":"the control key is wired to nothing","check":"press and observe"},'
              ' {"id":"no-score","hypothesis":"score never updates","check":"look for score++"}]')
_REFUTE_JSON = ('[{"id":"dead-control","verdict":"present","evidence":"keydown handler is empty"},'
                ' {"id":"no-score","verdict":"absent","evidence":"score increments on input"}]')


def main():
    problems = []

    # 1) hypotheses(): parse a good array; a garbage reply -> [].
    hyps = ra.hypotheses("a game", analyst_fn=lambda pr, model=None: _HYPS_JSON)
    if len(hyps) != 2 or hyps[0]["id"] != "dead-control" or not hyps[0]["hypothesis"]:
        problems.append("hypotheses() did not parse the stub array: %r" % hyps)
    if ra.hypotheses("a game", analyst_fn=lambda pr, model=None: "sorry, no json here") != []:
        problems.append("hypotheses() should return [] on an unparseable reply")

    # 2) refute(): present -> holes; a clean set -> clean.
    rep = ra.refute("a game", "<html>", hyps, analyst_fn=lambda pr, model=None: _REFUTE_JSON)
    if rep["verdict"] != "holes" or "dead-control" not in rep["present"]:
        problems.append("refute() did not surface the present hole: %r" % rep)
    clean = ra.refute("a game", "<html>", hyps,
                      analyst_fn=lambda pr, model=None: '[{"id":"dead-control","verdict":"absent","evidence":"ok"}]')
    if clean["verdict"] != "clean":
        problems.append("refute() with no present holes should be clean: %r" % clean)

    # 3) advisory: an analyst that RAISES or returns garbage -> inoperative, never propagates.
    def _boom(pr, model=None):
        raise RuntimeError("analyst down")
    try:
        inop = ra.refute("a game", "<html>", hyps, analyst_fn=_boom)
    except Exception as e:
        problems.append("a raising analyst propagated: %s" % e); inop = {}
    if inop.get("verdict") != "inoperative":
        problems.append("raising analyst not mapped to inoperative: %r" % inop)
    if ra.refute("a game", "<html>", hyps, analyst_fn=lambda pr, model=None: "garbage")["verdict"] != "inoperative":
        problems.append("garbage refute reply not mapped to inoperative")

    # 4) audit() composes both and carries the hypotheses.
    aud = ra.audit("a game", "<html>", analyst_fn=lambda pr, model=None: (_HYPS_JSON if "enumerate" in pr.lower()
                                                                          or "hypothes" in pr.lower() else _REFUTE_JSON))
    if not aud.get("hypotheses") or "verdict" not in aud:
        problems.append("audit() did not compose hypotheses+refute: %r" % aud)

    if problems:
        print("refute-lane gate: FAIL — " + " ;; ".join(problems))
        sys.exit(1)
    print("refute-lane gate: PASS — second-spec + refute pipeline works and is fail-safe advisory "
          "(present->holes, none->clean, analyst-down->inoperative, never raises); live red-team is opt-in")
    sys.exit(0)


if __name__ == "__main__":
    main()
