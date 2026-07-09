"""build_narrator.py — the HUMAN layer over the engine's technical output.

Every build produces two things now: the raw technical trace (what the engine did) AND this plain-English
interpretation (what it MEANS + what to do). `interpret(raw_engine_output)` parses the deterministic markers
in the engine's stdout — the metrics JSON verdict, the spec-review (loop #1) and targeted-repair (loop #2)
firings, and each attempt's failure reason — and renders a layman summary. Pure, never raises; used by
engine_runner to print the summary live AND to head the BUILD_TRACE.md report.
"""

import json
import re


def _metrics(raw):
    m = re.search(r"===METRICS_JSON_BEGIN===\s*(\{.*?\})\s*===METRICS_JSON_END===", raw or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _layman(why):
    """Translate one technical failure reason into plain English."""
    w = (why or "").lower()
    if "game over" in w or "instant" in w:
        return "the game was already OVER right after it started (instant death)"
    if "move up" in w and "dy=" in w:
        return "holding the control did NOT lift it — it fell instead (controls/physics wrong)"
    if "move down" in w and "dy=" in w:
        return "with no input it didn't fall as expected (physics off, or it measured a paused screen)"
    if "did not increase" in w or ("score" in w and "increase" in w):
        return "the score didn't go up when it should have"
    if "js error" in w or "undefined" in w or "cannot read" in w:
        return "the code CRASHED (a JavaScript error)"
    if "blank" in w or "empty" in w:
        return "the page rendered blank / empty"
    if "structural" in w:
        return "the file was missing required parts (" + (why or "")[:100] + ")"
    if "vanished" in w:
        return "the drawn content disappeared after input"
    return (why or "unknown")[:160]


def _advice(reasons, mx):
    r = reasons.lower()
    if "js error" in r or "undefined" in r or "cannot read" in r:
        return ("the model wrote buggy code. Targeted repair (loop #2) feeds the exact crash back, so re-running "
                "may converge; if it keeps crashing, use a more capable implementer.")
    if "move up" in r or "dy=" in r or "physics" in r:
        return ("the model didn't honor the physics in the spec. A dense single-file game is Lathe's HARDEST "
                "case — targeted repair helps, but consider a stronger implementer or splitting the page into "
                "smaller gated parts.")
    if mx.get("artifacts_total"):
        return ("a dense single-file page is the hardest case for a small/local model — try a more capable "
                "implementer, or split it into smaller pieces the harness can gate independently.")
    return "review the per-attempt reasons above; the spec or the model may need adjusting."


def interpret(raw, label=""):
    """Return a plain-English summary of a build from the engine's raw output. Never raises."""
    try:
        raw = raw or ""
        mx = _metrics(raw)
        fp, ft = mx.get("functions_passed"), mx.get("functions_total")
        ap, at = mx.get("artifacts_passed"), mx.get("artifacts_total")
        build_ok = mx.get("build_ok")
        loop1_warn = raw.count("[spec<->test WARNING]")
        loop1_fix = raw.count("[spec<->test REFINED]")
        loop2 = raw.count("[targeted repair]")
        fails = re.findall(r"attempt (\d+) FAILED . why: (.+)", raw)
        inop = "GATE INOPERATIVE" in raw

        out = ["=== WHAT HAPPENED (plain English) ==="]
        if label:
            out.append(label)
        if inop:
            out.append("~ COULD NOT JUDGE — the checker itself couldn't run (browser/environment), so this is "
                       "NOT a spec failure. Fix the environment (e.g. `python -m playwright install chromium`) and rerun.")
        elif build_ok:
            got = []
            if ft:
                got.append("%s/%s function(s)" % (fp, ft))
            if at:
                got.append("%s/%s file(s)" % (ap, at))
            out.append("[OK] SUCCESS — built and every check passed" + ((" (" + ", ".join(got) + ")") if got else "") + ".")
            if mx.get("pins_added"):
                out.append("  Saved (pinned) %s piece(s) so the exact result is reproducible." % mx["pins_added"])
        else:
            out.append("[X] NOTHING SHIPPED — the checks rejected every attempt.")

        if loop1_warn or loop1_fix:
            out.append("  - Spec self-review (loop #1): found %d contradiction(s) in the spec/test, fixed %d BEFORE building."
                       % (loop1_warn, loop1_fix))
        if loop2:
            out.append("  - Targeted repair (loop #2): fired %d time(s) — fed the exact failure back to fix it, not a blind retry."
                       % loop2)

        if fails:
            out.append("  Attempts:")
            for n, why in fails[:8]:
                out.append("    - attempt %s: %s" % (n, _layman(why)))

        if not build_ok and not inop:
            out.append("WHAT TO DO: " + _advice(" ".join(w for _, w in fails), mx))

        if mx.get("elapsed_s") is not None:
            out.append("  (took ~%ss)" % round(mx.get("elapsed_s")))
        return "\n".join(out)
    except Exception as e:
        return "=== WHAT HAPPENED ===\n(could not interpret the build output: %s)" % str(e)[:120]
