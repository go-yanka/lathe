"""behavioral_gate.py — TRUSTED behavioral-intent interpreter (hand-authored CORE_INFRA; never model-written).

MASTER_PLAN D1. The `web_canvas_game` liveness gate only proves the canvas CHANGES over time — a helicopter
that falls and dies still "changes", so DEAD CONTROLS pass it (the helicopter class: game ends the instant it
starts because holding the thrust key does nothing). This module closes that hole.

Design (owner's "declarative intents, run by a trusted engine interpreter"):
  - The ANALYST authors a behavioral spec as pure DATA — a list of independent TRIALS. It carries NO code.
  - Each trial: a DRIVE (what input to apply, from a fixed verb set) + an EXPECT (what the foreground should
    then do, from a fixed assertion set). Example for a helicopter:
        [ {"hold": "Space", "ms": 800, "expect": "up"},     # holding thrust makes the craft RISE
          {"idle": 800, "expect": "down"} ]                 # with no input, gravity pulls it DOWN
  - `build_script(behavior)` compiles that DATA into a trusted Playwright script (the interpreter). The analyst
    can ONLY pick from the fixed vocabulary; an unknown verb/assertion makes build_script RAISE -> the engine
    refuses the build (fail closed, same contract as an unknown functional_ref).

How "did the input do the right thing?" is observed WITHOUT the game cooperating: each trial loads the page
FRESH, samples the canvas foreground CENTROID (centre of mass of non-background pixels) before and after the
drive, and asserts the centroid moved as EXPECTED. A dead-control helicopter falls under both drive and idle,
so its `hold ... expect up` trial fails: proof the control is inert.

Vocabulary (fixed):
  drive verbs   : hold {key, ms} | press {key} | idle {ms} | click {x, y}
  expect verbs  : up | down | left | right | move | still
Threshold: a centroid delta counts only if it exceeds MIN_FRAC of the canvas dimension (noise floor).
"""

import json

DRIVE_VERBS = ("hold", "press", "idle", "click")
EXPECT_VERBS = ("up", "down", "left", "right", "move", "still")
MIN_FRAC = 0.04   # a move must exceed 4% of the canvas dimension to count (below = jitter/noise)


def _validate(behavior):
    """Return a list of normalized trials or raise ValueError (build_script fails closed on bad DATA)."""
    if not isinstance(behavior, list) or not behavior:
        raise ValueError("behavior must be a non-empty list of trial dicts")
    trials = []
    for i, t in enumerate(behavior):
        if not isinstance(t, dict):
            raise ValueError("trial %d is not an object" % i)
        drive = [k for k in DRIVE_VERBS if k in t]
        if len(drive) != 1:
            raise ValueError("trial %d must name exactly one drive verb %s, got %r"
                             % (i, DRIVE_VERBS, list(t.keys())))
        verb = drive[0]
        val = t[verb]                       # the drive verb is keyed to its argument (owner's DATA form)
        exp = t.get("expect")
        if exp not in EXPECT_VERBS:
            raise ValueError("trial %d expect must be one of %s, got %r" % (i, EXPECT_VERBS, exp))
        norm = {"verb": verb, "expect": exp}
        if verb in ("hold", "press"):
            # {"hold": "Space", "ms": 900}: value is the key; ms is the hold/settle window.
            if not isinstance(val, str) or not val:
                raise ValueError("trial %d %s value must be a non-empty key string, got %r" % (i, verb, val))
            norm["key"] = val
            norm["ms"] = int(t.get("ms", 700))
        elif verb == "idle":
            # {"idle": 900}: value is the wait in ms (ms field also honored as a fallback).
            norm["ms"] = int(val if isinstance(val, (int, float)) else t.get("ms", 700))
        elif verb == "click":
            # {"click": [x, y], "ms": 700}: value is the click point.
            if not (isinstance(val, (list, tuple)) and len(val) == 2):
                raise ValueError("trial %d click value must be [x, y], got %r" % (i, val))
            norm["x"] = int(val[0]); norm["y"] = int(val[1]); norm["ms"] = int(t.get("ms", 700))
        trials.append(norm)
    return trials


# JS measuring the foreground centroid: centre of mass of pixels that differ from the top-left (assumed bg).
# Returns {x, y, n, w, h}; n==0 means an empty/blank canvas (fail: nothing drawn).
_CENTROID_JS = r"""
c => {
  const ctx = c.getContext('2d'); if (!ctx) return {x:-1,y:-1,n:0,w:c.width,h:c.height};
  const w = c.width, h = c.height, d = ctx.getImageData(0,0,w,h).data;
  const br=d[0], bg=d[1], bb=d[2];
  let sx=0, sy=0, n=0;
  for (let y=0; y<h; y+=3){ for (let x=0; x<w; x+=3){ const i=(y*w+x)*4;
    if (Math.abs(d[i]-br)+Math.abs(d[i+1]-bg)+Math.abs(d[i+2]-bb) > 60){ sx+=x; sy+=y; n++; } } }
  return n ? {x:sx/n, y:sy/n, n:n, w:w, h:h} : {x:-1,y:-1,n:0,w:w,h:h};
}
"""


def build_script(behavior):
    """Compile a DATA behavioral spec into a trusted Playwright gate script (string). Raises on bad DATA."""
    trials = _validate(behavior)
    return (
        "import os\n"
        "from playwright.sync_api import sync_playwright\n"
        "path = os.environ['ARTIFACT_FILE']\n"
        "url = 'file:///' + path.replace(os.sep, '/')\n"
        "TRIALS = " + json.dumps(trials) + "\n"
        "MIN_FRAC = " + repr(MIN_FRAC) + "\n"
        "CENTROID = " + json.dumps(_CENTROID_JS) + "\n"
        "fails = []\n"
        "with sync_playwright() as p:\n"
        "    browser = p.chromium.launch()\n"
        "    for t in TRIALS:\n"
        "        errors = []\n"
        "        page = browser.new_page()\n"
        "        page.on('pageerror', lambda e: errors.append(str(e)))\n"
        "        page.goto(url)\n"
        "        page.wait_for_timeout(400)\n"
        "        page.mouse.click(300, 300)          # focus / dismiss a press-to-start overlay\n"
        "        page.wait_for_timeout(150)          # brief settle — short, so a falling object is not already floored at c0\n"
        "        try:\n"
        "            c0 = page.eval_on_selector('canvas', CENTROID)\n"
        "        except Exception as e:\n"
        "            fails.append('no canvas: ' + str(e)[:80]); page.close(); continue\n"
        "        if not c0 or c0['n'] == 0:\n"
        "            fails.append(repr(t) + ' -> canvas is blank before the drive'); page.close(); continue\n"
        "        v = t['verb']\n"
        "        if v == 'hold':\n"
        "            page.keyboard.down(t['key']); page.wait_for_timeout(t['ms']); page.keyboard.up(t['key'])\n"
        "        elif v == 'press':\n"
        "            page.keyboard.press(t['key']); page.wait_for_timeout(t['ms'])\n"
        "        elif v == 'click':\n"
        "            page.mouse.click(t['x'], t['y']); page.wait_for_timeout(t['ms'])\n"
        "        else:\n"
        "            page.wait_for_timeout(t['ms'])   # idle\n"
        "        c1 = page.eval_on_selector('canvas', CENTROID)\n"
        "        if errors:\n"
        "            fails.append(repr(t) + ' -> JS error: ' + ' | '.join(errors[:2]))\n"
        "        if not c1 or c1['n'] == 0:\n"
        "            fails.append(repr(t) + ' -> foreground vanished after the drive (blank canvas)'); page.close(); continue\n"
        "        dx = c1['x'] - c0['x']; dy = c1['y'] - c0['y']\n"
        "        tx = MIN_FRAC * c0['w']; ty = MIN_FRAC * c0['h']\n"
        "        exp = t['expect']; ok = True; why = ''\n"
        "        if exp == 'up':      ok = dy < -ty; why = 'expected foreground to move UP (dy=%.1f, need<%.1f)' % (dy, -ty)\n"
        "        elif exp == 'down':  ok = dy >  ty; why = 'expected foreground to move DOWN (dy=%.1f, need>%.1f)' % (dy, ty)\n"
        "        elif exp == 'left':  ok = dx < -tx; why = 'expected foreground to move LEFT (dx=%.1f, need<%.1f)' % (dx, -tx)\n"
        "        elif exp == 'right': ok = dx >  tx; why = 'expected foreground to move RIGHT (dx=%.1f, need>%.1f)' % (dx, tx)\n"
        "        elif exp == 'move':  ok = (abs(dx) > tx or abs(dy) > ty); why = 'expected motion (dx=%.1f dy=%.1f)' % (dx, dy)\n"
        "        elif exp == 'still': ok = (abs(dx) <= tx and abs(dy) <= ty); why = 'expected NO motion (dx=%.1f dy=%.1f)' % (dx, dy)\n"
        "        if not ok:\n"
        "            fails.append(repr(t) + ' -> ' + why)\n"
        "        page.close()\n"
        "    browser.close()\n"
        "assert not fails, 'BEHAVIORAL FAIL: ' + ' ;; '.join(fails)\n"
        "print('BEHAVIORAL PASS: %d trial(s) — inputs produce the specified foreground response' % len(TRIALS))\n"
    )
