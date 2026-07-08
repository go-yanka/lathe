"""vision_judge.py — MASTER_PLAN D3: an ADVISORY visual judge for rendered web artifacts.

Deterministic gates prove a page loads, animates, responds to input, and keeps state (D1/D2). They cannot see
that it LOOKS like what the goal asked for — a page can pass every structural/behavioral check and still render
as a blank rectangle, an off-topic layout, or an unstyled mess. D3 closes that by SHOWING a screenshot of the
running app to a vision-capable model and asking "does this look like a working <goal>?".

This is ADVISORY by design: vision judgement is fuzzy, so the verdict is recorded in the manifest/report and,
by default, NEVER hard-fails a build (LATHE_VISION_JUDGE=strict opts into failing on a high-confidence "no").
The model call reuses the SSRF-guarded analyst client (request_spec, with the new `images=` path); the judge
endpoint is therefore the same loopback proxy the analyst uses.

Split of what is PROVEN:
  - the PLUMBING (screenshot -> encode -> judge -> parse -> advisory verdict) is proven deterministically by
    qa/vision_lane_gate.py against a stub judge (no model, runs in the standing suite);
  - the LIVE model judgement is inherently non-deterministic (like the rig): demonstrated on demand via
    `judge_live`, not run on every build.
"""

import base64
import json
import os
import re


def capture(html_path, out_png=None, width=900, height=650, settle_ms=700):
    """Screenshot a local HTML file in headless Chromium. Returns the PNG bytes (and writes out_png if given).
    Raises on capture failure — the caller decides whether that is advisory or fatal."""
    from playwright.sync_api import sync_playwright
    url = "file:///" + os.path.abspath(html_path).replace(os.sep, "/")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(url)
        page.wait_for_timeout(settle_ms)          # let first paint / initial animation settle
        png = page.screenshot(type="png")
        browser.close()
    if out_png:
        with open(out_png, "wb") as f:
            f.write(png)
    return png


_PROMPT = (
    "You are a STRICT visual QA reviewer. The build goal was:\n\n  {goal}\n\n"
    "Attached is a screenshot of the running page. Judge ONLY what you can SEE. Reply with COMPACT JSON and "
    "nothing else: {{\"looks_right\": true|false, \"confidence\": 0.0-1.0, \"issues\": [\"short phrase\", ...]}}. "
    "Set looks_right=false if the page is blank/empty, visibly broken or unstyled, shows an error, or clearly "
    "does not depict what the goal describes. Keep issues to at most 4 short phrases."
)


def parse_verdict(text):
    """Parse the model's reply into {looks_right, confidence, issues}. Lenient: pulls the first JSON object,
    falls back to a keyword read. Returns None if nothing usable (caller treats as inoperative/advisory)."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group())
            lr = d.get("looks_right")
            if isinstance(lr, str):
                lr = lr.strip().lower() in ("true", "yes", "1")
            return {"looks_right": bool(lr),
                    "confidence": float(d.get("confidence", 0.5)) if str(d.get("confidence", "")).strip() else 0.5,
                    "issues": [str(x) for x in (d.get("issues") or [])][:4]}
        except Exception:
            pass
    low = text.lower()                            # fallback if the model wrapped prose around no/failed
    if "looks_right" in low or "blank" in low or "broken" in low or "empty" in low:
        bad = any(w in low for w in ("false", "blank", "broken", "empty", "not ", "does not"))
        return {"looks_right": not bad, "confidence": 0.3, "issues": ["parsed from prose"]}
    return None


def judge(png_bytes, goal, judge_fn=None, model=None):
    """Advisory visual verdict for a screenshot. `judge_fn(prompt, image_data_uri)->reply_text` is injectable
    (the standing gate passes a stub; production passes the real analyst client). Returns a dict:
       {"verdict": "pass"|"fail"|"inoperative", "looks_right": bool|None, "confidence": float, "issues": [...]}
    NEVER raises — a judge outage is 'inoperative' (advisory), not a crash."""
    uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    prompt = _PROMPT.format(goal=goal)
    if judge_fn is None:
        def judge_fn(pr, image_uri):
            import request_spec
            return request_spec.request_spec(
                pr, images=[image_uri], model=model or os.environ.get("LATHE_VISION_MODEL", "sonnet"),
                timeout=int(os.environ.get("LATHE_VISION_TIMEOUT", "90")))
    try:
        reply = judge_fn(prompt, uri)
    except Exception as e:                        # advisory: a broken judge never breaks the build
        return {"verdict": "inoperative", "looks_right": None, "confidence": 0.0,
                "issues": ["judge call failed: %s" % str(e)[:100]]}
    v = parse_verdict(reply)
    if v is None:
        return {"verdict": "inoperative", "looks_right": None, "confidence": 0.0,
                "issues": ["no parseable verdict from the judge"]}
    return {"verdict": "pass" if v["looks_right"] else "fail",
            "looks_right": v["looks_right"], "confidence": v["confidence"], "issues": v["issues"]}


def judge_live(html_path, goal, model=None):
    """Convenience: capture + judge with the REAL analyst client. Used for the live demonstration / opt-in
    build-time judging. Advisory; returns the judge() dict (or an inoperative dict if capture fails)."""
    try:
        png = capture(html_path)
    except Exception as e:
        return {"verdict": "inoperative", "looks_right": None, "confidence": 0.0,
                "issues": ["screenshot failed: %s" % str(e)[:100]]}
    return judge(png, goal, model=model)
