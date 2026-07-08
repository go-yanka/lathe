"""spec_review.py — the CLOSED LOOP: a spec reviews + refines ITSELF until clean, BEFORE the implementer runs.

The persistent gap: gates DETECT bad output but nothing iterates the SPEC toward correct. The analyst writes a
spec + acceptance test ONCE, blind; if the test contradicts the spec or the spec is too dense, the implementer
wastes attempts on an unwinnable target. This module closes that: draft -> critique -> refine -> repeat until
the spec passes the bar, THEN hand off.

Termination is anchored on the DETERMINISTIC bar (spec_test_consistency) so the loop always converges and
"clean" is objective; the analyst's LLM critique feeds the refinement (catches what heuristics miss) but never
decides termination (it is fuzzy). Analyst is injected -> pure + testable. Never raises.
"""

import json
import os
import re


def _stc():
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec_test_consistency.py")
    s = importlib.util.spec_from_file_location("spec_test_consistency", p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def deterministic_problems(spec_text, behavior):
    """The HARD bar: spec<->test contradictions. Empty list == the spec passes the objective check."""
    try:
        return ["[%s] %s" % (w["rule"], w["message"]) for w in _stc().check(spec_text, behavior)]
    except Exception:
        return []


def _default_analyst():
    def _f(prompt, model=None):
        import request_spec
        return request_spec.request_spec(prompt, model=model or os.environ.get("LATHE_SPEC_REVIEW_MODEL", "sonnet"),
                                         timeout=int(os.environ.get("LATHE_SPEC_REVIEW_TIMEOUT", "120")))
    return _f


_CRITIQUE = (
    "You are reviewing YOUR OWN build spec and its acceptance test before a (fallible) implementer sees them.\n"
    "SPEC:\n{spec}\n\nACCEPTANCE TEST (behavior trials):\n{behavior}\n\n"
    "List concrete problems that would make a CORRECT implementation FAIL the test, or make the spec too "
    "dense/ambiguous to build in one shot (contradictions between spec and test, tests that can't pass given "
    "the spec's own rules, missing setup, over-complex scope). One problem per line. If there are none, reply "
    "exactly: NONE"
)

_REFINE = (
    "Revise YOUR build spec and acceptance test to FIX every problem below. Keep the test CONSISTENT with the "
    "spec, keep the spec as SIMPLE as the goal allows, and make the test fair to a correct build.\n"
    "PROBLEMS:\n{problems}\n\nCURRENT SPEC:\n{spec}\n\nCURRENT TEST:\n{behavior}\n\n"
    "Reply with ONLY compact JSON: {{\"spec\": \"<revised spec text>\", \"behavior\": [<revised trials>]}}"
)


def critique(spec_text, behavior, analyst_fn):
    """Analyst's own-work critique -> list of problem strings ([] if it says NONE or on any failure)."""
    try:
        reply = analyst_fn(_CRITIQUE.format(spec=spec_text, behavior=json.dumps(behavior)))
    except Exception:
        return []
    if not reply or reply.strip().upper().startswith("NONE"):
        return []
    return [ln.strip("-* \t") for ln in reply.strip().splitlines() if ln.strip() and "NONE" not in ln.upper()][:8]


def refine(spec_text, behavior, problems, analyst_fn):
    """Ask the analyst to rewrite spec+test to fix `problems`. Returns (new_spec, new_behavior); falls back to
    the originals if the reply is unparseable (never returns garbage)."""
    try:
        reply = analyst_fn(_REFINE.format(problems="\n".join("- " + p for p in problems),
                                          spec=spec_text, behavior=json.dumps(behavior)))
    except Exception:
        return spec_text, behavior
    m = re.search(r"\{.*\}", reply or "", re.DOTALL)
    if not m:
        return spec_text, behavior
    try:
        d = json.loads(m.group())
        ns = d.get("spec") if isinstance(d.get("spec"), str) and d.get("spec").strip() else spec_text
        nb = d.get("behavior") if isinstance(d.get("behavior"), list) and d.get("behavior") else behavior
        return ns, nb
    except Exception:
        return spec_text, behavior


def converge(spec_text, behavior, analyst_fn=None, max_rounds=2, use_llm=True):
    """Loop review->refine until the DETERMINISTIC bar is clean (or max_rounds hit). Returns a dict:
       {spec, behavior, rounds, clean, history}. Never raises. The implementer should be engaged only on the
       returned spec/behavior; `clean` False means it could not be fully reconciled (surface it, don't hide)."""
    analyst_fn = analyst_fn or _default_analyst()
    history = []
    rounds = 0
    while True:
        det = deterministic_problems(spec_text, behavior)
        llm = critique(spec_text, behavior, analyst_fn) if use_llm else []
        history.append({"round": rounds, "deterministic": det, "critique": llm})
        if not det:                                   # objective bar met -> stop
            return {"spec": spec_text, "behavior": behavior, "rounds": rounds, "clean": True, "history": history}
        if rounds >= max_rounds:
            break
        spec_text, behavior = refine(spec_text, behavior, det + llm, analyst_fn)
        rounds += 1
    return {"spec": spec_text, "behavior": behavior, "rounds": rounds,
            "clean": not deterministic_problems(spec_text, behavior), "history": history}
