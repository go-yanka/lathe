"""spec_test_consistency.py — catch a build spec that CONTRADICTS its own acceptance test (the "crap input"
class), BEFORE the implementer wastes attempts on an unwinnable target.

The analyst authors BOTH the build spec (the artifact prompt) AND the behavioral acceptance test (the `behavior`
trials). If the test contradicts the spec, even a CORRECT build fails — the implementer can't win. Real case
(2026-07-08 helicopter): the spec said "no obstacles for the FIRST 5 SECONDS" while the test said "hold Space
1.2s -> #score must INCREASE". Score is obstacle/distance based, so in 1.2s it is legitimately still 0 — a
working copter was rejected by its own test. This module flags that BEFORE the build.

Pure `check(spec_text, behavior) -> [warnings]`. Deterministic heuristics (no model call), each a named rule.
Never raises. Advisory by default; under LATHE_SPEC_TEST_STRICT the engine refuses the build so the analyst
must fix the TEST rather than re-rolling the artifact against a broken target.
"""

import re

_SCORE_NAMES = ("score", "points", "pts", "count", "counter", "distance")


def _bare(selector):
    return re.sub(r"^[#.]", "", (selector or "").strip()).lower()


def _grace_ms(spec_low):
    """If the spec describes a period during which nothing scores (grace / no obstacles for N seconds), return
    that window in ms, else None. Only counts a number that sits in a grace/no-score context."""
    best = None
    for m in re.finditer(r"(\d+)\s*second", spec_low):
        n = int(m.group(1))
        ctx = spec_low[max(0, m.start() - 60):m.end() + 20]
        if any(w in ctx for w in ("grace", "no obstacle", "no obstacles", "first", "before the first", "no score")):
            best = max(best or 0, n)
    return best * 1000 if best else None


def check(spec_text, behavior):
    """Return a list of {rule, trial, message} warnings where the acceptance test contradicts the spec."""
    warns = []
    if not isinstance(behavior, list):
        return warns
    spec_low = (spec_text or "").lower()
    grace = _grace_ms(spec_low)

    for i, t in enumerate(behavior):
        if not isinstance(t, dict):
            continue
        st = t.get("state")
        ms = int(t.get("ms", 700)) if str(t.get("ms", "")).strip().lstrip("-").isdigit() else 700

        if isinstance(st, dict) and st.get("kind", "selector") == "selector" and st.get("selector"):
            bare = _bare(st["selector"])
            # R1 selector-undeclared: the test checks an element the spec never says to create.
            if bare and bare not in spec_low:
                warns.append({"rule": "selector-undeclared", "trial": i,
                              "message": "test asserts on '%s' but the spec never mentions creating that element"
                                         % st["selector"]})
            # R2 score-vs-grace: a score-increase trial whose window is inside a stated no-score grace period.
            if st.get("op") == "increases" and any(n in bare for n in _SCORE_NAMES) and grace and ms < grace:
                warns.append({"rule": "score-vs-grace", "trial": i,
                              "message": "test expects '%s' to INCREASE within %dms, but the spec states a "
                                         "~%dms grace/no-score period — a correct build scores 0 here and fails"
                                         % (st["selector"], ms, grace)})

        # R3 motion-vs-paused: a motion trial while the spec says the game starts PAUSED and the test does not
        # start it (no press/hold drive) — it would measure a paused screen.
        if t.get("expect") in ("up", "down", "left", "right", "move") and t.get("idle") is not None:
            if any(w in spec_low for w in ("press to start", "click to start", "starts paused", "start screen")):
                warns.append({"rule": "motion-vs-paused", "trial": i,
                              "message": "an IDLE trial expects motion, but the spec says the game starts "
                                         "paused (press/click to start) — an idle run may measure a paused screen"})
    return warns


def summary(warns):
    if not warns:
        return "spec<->test consistent"
    return "%d spec<->test contradiction(s): " % len(warns) + " ;; ".join(
        "[%s] %s" % (w["rule"], w["message"]) for w in warns)
