"""refute_auditor.py — MASTER_PLAN C1/C2: the per-build ADVERSARIAL second spec + refute pass.

Owner's design: a build carries TWO specs — one to DO the work, and one for "what could go wrong with ANY LLM
doing this". The second must not be re-imagined by the same model that built it (shared blind spots); the
DURABLE part is the failure-mode registry (C3/4/5, already shipped). This module adds the per-goal LIVE arm:

  C1  hypotheses(goal)  — the analyst enumerates concrete failure hypotheses for THIS goal ("how could any LLM
      get this wrong"): the second spec. Recorded in the manifest alongside the assumptions.
  C2  refute(goal, artifact, hypotheses) — a post-build pass that ASSUMES the work is broken and, for each
      hypothesis, judges whether the artifact exhibits it. Advisory: it annotates the report and surfaces
      candidate new failure classes (which graduate into the registry via C4), but does not by itself fail the
      build — the deterministic gates decide pass/fail.

Same honest split as the vision judge: the PLUMBING (generate -> parse -> refute -> parse -> advisory report)
is proven deterministically by qa/refute_lane_gate.py with a stub analyst; the LIVE model red-team is
non-deterministic and validated on demand. Reuses the SSRF-guarded analyst client (request_spec). Never raises.
"""

import json
import os
import re


def _default_analyst():
    def _f(prompt, model=None):
        import request_spec
        return request_spec.request_spec(prompt, model=model or os.environ.get("LATHE_REDTEAM_MODEL", "sonnet"),
                                         timeout=int(os.environ.get("LATHE_REDTEAM_TIMEOUT", "120")))
    return _f


def _extract_list(text):
    """Pull the first JSON array of objects from a model reply. Returns [] if none."""
    if not text:
        return []
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        v = json.loads(m.group())
        return v if isinstance(v, list) else []
    except Exception:
        return []


_HYP_PROMPT = (
    "You are an adversarial reviewer. A DIFFERENT model will build the following goal:\n\n  {goal}\n\n"
    "Enumerate the concrete ways ANY LLM implementer is LIKELY to get this specific goal WRONG — the silent "
    "wrong-guesses, missing behaviors, and 'passes a shallow check but is actually broken' traps. Do NOT "
    "restate the goal or list generic advice. Reply with ONLY a JSON array, 3-8 items, each:\n"
    '  {{"id": "kebab-slug", "hypothesis": "the specific way it breaks", "check": "how to tell if it happened"}}'
)

_REFUTE_PROMPT = (
    "You are refuting a build: ASSUME it is broken and try to prove it. The goal was:\n\n  {goal}\n\n"
    "Here is the produced artifact (truncated):\n---\n{artifact}\n---\n\n"
    "For each failure hypothesis below, judge from the artifact whether it is PRESENT (the build exhibits the "
    "flaw), ABSENT (clearly handled), or UNCLEAR. Be skeptical; default to UNCLEAR when you cannot tell.\n"
    "Hypotheses:\n{hyps}\n\n"
    "Reply with ONLY a JSON array, one item per hypothesis:\n"
    '  {{"id": "matching-slug", "verdict": "present|absent|unclear", "evidence": "short reason"}}'
)


def hypotheses(goal, analyst_fn=None, model=None):
    """C1: the analyst's second spec — concrete failure hypotheses for this goal. Returns a list (possibly
    empty on outage). Never raises."""
    analyst_fn = analyst_fn or _default_analyst()
    try:
        reply = analyst_fn(_HYP_PROMPT.format(goal=goal), model=model)
    except Exception:
        return []
    out = []
    for h in _extract_list(reply):
        if isinstance(h, dict) and h.get("hypothesis"):
            out.append({"id": str(h.get("id", "")).strip() or "hole-%d" % len(out),
                        "hypothesis": str(h["hypothesis"])[:300],
                        "check": str(h.get("check", ""))[:300]})
    return out[:8]


def refute(goal, artifact_text, hyps, analyst_fn=None, model=None, max_artifact=12000):
    """C2: the refute pass — for each hypothesis, does the artifact exhibit it? Returns a report dict:
       {"verdicts": [{id, verdict, evidence}], "present": [...ids...], "verdict": "clean|holes|inoperative"}
    Advisory. Never raises."""
    if not hyps:
        return {"verdicts": [], "present": [], "verdict": "inoperative", "note": "no hypotheses to refute"}
    analyst_fn = analyst_fn or _default_analyst()
    _hyps_txt = "\n".join("- %s: %s" % (h["id"], h["hypothesis"]) for h in hyps)
    _art = (artifact_text or "")[:max_artifact]
    try:
        reply = analyst_fn(_REFUTE_PROMPT.format(goal=goal, artifact=_art, hyps=_hyps_txt), model=model)
    except Exception as e:
        return {"verdicts": [], "present": [], "verdict": "inoperative", "note": "refute call failed: %s" % str(e)[:100]}
    verdicts = []
    for v in _extract_list(reply):
        if isinstance(v, dict) and v.get("verdict"):
            verdicts.append({"id": str(v.get("id", "")).strip(),
                             "verdict": str(v["verdict"]).strip().lower(),
                             "evidence": str(v.get("evidence", ""))[:240]})
    if not verdicts:
        return {"verdicts": [], "present": [], "verdict": "inoperative", "note": "no parseable refute verdicts"}
    present = [v["id"] for v in verdicts if v["verdict"] == "present"]
    return {"verdicts": verdicts, "present": present, "verdict": "holes" if present else "clean"}


def audit(goal, artifact_text, analyst_fn=None, model=None):
    """Convenience C1+C2: generate the second spec, then refute the artifact against it. Advisory report."""
    hyps = hypotheses(goal, analyst_fn=analyst_fn, model=model)
    rep = refute(goal, artifact_text, hyps, analyst_fn=analyst_fn, model=model)
    rep["hypotheses"] = hyps
    return rep
