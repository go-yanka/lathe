"""func_gates.py — TRUSTED functional-gate registry (hand-authored CORE_INFRA; never model-written).

Model-drafted plans are DATA and must not carry raw executable gate code (plan_validator refuses a raw
"functional" field in untrusted plans — it runs as code). Instead a plan references a gate BY NAME via
  "functional_ref": "<name>"
and the engine resolves the name here at build time. The scripts below run as subprocesses against the
generated artifact (path in $ARTIFACT_FILE), exit 0 = pass — same contract as engine_v2._func_test.

Security invariants:
  - this file is in engine_v2._CORE_INFRA, so a plan's MODULE_NAME can never overwrite it;
  - refs resolve ONLY from this dict — an unknown ref is a loud build refusal, never a silent skip;
  - scripts receive a secret-scrubbed env (engine strips key/token/cred vars before the subprocess).
"""

# name -> python source of the gate script (run with the same interpreter as the engine)
FUNC_GATES = {
    # Any static web page: loads in real Chromium with zero JS errors and a non-trivial rendered body.
    "web_page": r'''
import os
from playwright.sync_api import sync_playwright
path = os.environ["ARTIFACT_FILE"]
url = "file:///" + path.replace(os.sep, "/")
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_timeout(500)
    body_len = page.evaluate("document.body ? document.body.innerText.length + document.body.children.length : 0")
    browser.close()
assert not errors, "JS errors on the page: " + " | ".join(errors[:3])
assert body_len > 0, "page rendered an empty body"
print("FUNCTIONAL PASS: page loads, no JS errors, non-empty body")
''',

    # An interactive canvas app/game: canvas present, responds to keys, and actually animates
    # (two frames sampled ~0.7s apart must differ), with zero JS errors.
    "web_canvas_game": r'''
import os
from playwright.sync_api import sync_playwright
path = os.environ["ARTIFACT_FILE"]
url = "file:///" + path.replace(os.sep, "/")
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_timeout(400)
    page.mouse.click(300, 300)                # focus / dismiss any "press to start"
    size = page.eval_on_selector("canvas", "c => ({w: c.width, h: c.height})")
    assert size["w"] > 0 and size["h"] > 0, "canvas has zero size"
    # D2 instant-game-over guard: a game must not already be OVER right after it starts (the helicopter
    # symptom — "the game ends as soon as it starts"). Checked EARLY (before we drive keys), and only on
    # VISIBLE text (innerText), so a hidden overlay or a working game that a later drive legitimately loses
    # is not false-failed. Loss-only phrases only (a start screen says "press to start", not "you lose").
    page.wait_for_timeout(700)
    _early = (page.evaluate("() => document.body ? (document.body.innerText || '') : ''") or "").lower()
    for _p in ("game over", "you lose", "you died", "you crashed", "try again", "game_over"):
        assert _p not in _early, "game is already OVER right after start (found %r) - unplayable/instant-death" % _p
    for k in ("Space", "ArrowRight", "ArrowLeft", "Space"):
        page.keyboard.press(k)
        page.wait_for_timeout(120)
    frame_a = page.eval_on_selector("canvas", "c => c.toDataURL()")
    # A CORRECT slow-tick game (Tetris gravity ~1s at level 1) can be still for 700ms — that false-failed
    # a WORKING 9B build. Force movement (soft drop) and observe across a window longer than one tick.
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(600)
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(900)
    frame_b = page.eval_on_selector("canvas", "c => c.toDataURL()")
    browser.close()
assert not errors, "JS errors on the page: " + " | ".join(errors[:3])
assert frame_a != frame_b, "canvas did not change over time - not a live/animating app"
print("FUNCTIONAL PASS: canvas present, no JS errors, animates after input")
''',
}


def resolve(ref):
    """Gate source for a registered ref, or None (caller must refuse the build on None — fail closed)."""
    if not isinstance(ref, str):
        return None
    return FUNC_GATES.get(ref.strip())
