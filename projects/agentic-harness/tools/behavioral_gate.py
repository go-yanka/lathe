"""behavioral_gate.py — TRUSTED behavioral-intent interpreter (hand-authored CORE_INFRA; never model-written).

MASTER_PLAN D1 + D2. The `web_canvas_game` liveness gate only proves the canvas CHANGES over time — a
helicopter that falls and dies still "changes", so DEAD CONTROLS pass it (the helicopter class: the game ends
the instant it starts because holding the thrust key does nothing). This module closes that hole and adds
STATE assertions (score progresses, "game over" is absent) so a build is never certified on motion alone.

Design (owner's "declarative intents, run by a trusted engine interpreter"):
  - The ANALYST authors a behavioral spec as pure DATA — a list of independent TRIALS. It carries NO code.
  - Each trial has a DRIVE (input to apply, from a fixed verb set) and at least one ASSERTION:
      * "expect"  — a foreground-MOTION check (D1): up|down|left|right|move|still.
      * "state"   — a DOM-STATE check (D2): a named element's text must change/increase/stay, or a page
                    phrase must be present/absent (e.g. "game over" must NOT appear after correct play).
    Example helicopter (D1):  {"hold": "Space", "ms": 900, "expect": "up"}
    Example scorer (D2):      {"press": "Space", "state": {"selector": "#score", "op": "increases"}}
    Example not-dead (D2):    {"idle": 900, "state": {"text_absent": "game over"}}
  - `build_script(behavior)` compiles that DATA into a trusted Playwright script (the interpreter). The analyst
    can ONLY pick from the fixed vocabulary; an unknown verb/op makes build_script RAISE -> the engine refuses
    the build (fail closed, same contract as an unknown functional_ref).

Motion is observed WITHOUT the game cooperating: each trial loads the page FRESH, samples the canvas
foreground CENTROID (centre of mass of non-background pixels) before and after the drive. State is observed by
reading DOM text before/after. A dead-control helicopter falls under both drive and idle, so its
`hold ... expect up` trial fails; a game whose score never moves fails its `increases` trial.

Vocabulary (fixed):
  drive verbs   : hold {key, ms} | press {key} | idle {ms} | click {[x, y]}
  expect verbs  : up | down | left | right | move | still
  state ops     : {"selector": <css>, "op": changes|increases|stable} | {"text_absent": <s>} | {"text_present": <s>}
Threshold: a centroid delta counts only if it exceeds MIN_FRAC of the canvas dimension (noise floor).
"""

import json

DRIVE_VERBS = ("hold", "press", "idle", "click")
EXPECT_VERBS = ("up", "down", "left", "right", "move", "still")
STATE_OPS = ("changes", "increases", "stable")
MIN_FRAC = 0.04   # a move must exceed 4% of the canvas dimension to count (below = jitter/noise)


def _validate_state(i, st):
    """Validate a trial's optional `state` assertion. Return normalized dict or raise."""
    if not isinstance(st, dict):
        raise ValueError("trial %d state must be an object" % i)
    if "text_absent" in st or "text_present" in st:
        key = "text_absent" if "text_absent" in st else "text_present"
        if not isinstance(st[key], str) or not st[key]:
            raise ValueError("trial %d state %s must be a non-empty string" % (i, key))
        return {"kind": key, "text": st[key]}
    sel = st.get("selector"); op = st.get("op")
    if not isinstance(sel, str) or not sel:
        raise ValueError("trial %d state needs a 'selector' string (or text_absent/text_present)" % i)
    if op not in STATE_OPS:
        raise ValueError("trial %d state op must be one of %s, got %r" % (i, STATE_OPS, op))
    return {"kind": "selector", "selector": sel, "op": op}


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
        st = t.get("state")
        if exp is None and st is None:
            raise ValueError("trial %d needs at least one assertion: 'expect' (motion) or 'state' (DOM)" % i)
        if exp is not None and exp not in EXPECT_VERBS:
            raise ValueError("trial %d expect must be one of %s, got %r" % (i, EXPECT_VERBS, exp))
        norm = {"verb": verb, "expect": exp, "state": _validate_state(i, st) if st is not None else None}
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

# Stash the canvas pixels right before the drive so the after-drive pass can isolate what MOVED.
_STASH_JS = ("() => { const c = document.querySelector('canvas'); if (c) { const x = c.getContext('2d'); "
             "if (x) window.__latheBefore = x.getImageData(0,0,c.width,c.height).data; } }")

# Genre-robust MOTION measure: the whole-scene centroid is swamped by large STATIC regions (e.g. Breakout's
# brick wall), so a moving paddle barely shifts it. Instead, look ONLY at pixels that CHANGED vs the stashed
# 'before' frame — that is the moving element(s) — and measure how their non-bg mass shifted (from-position in
# 'before' -> to-position in 'after'). Static scenery drops out; the controlled element's displacement shows.
_MOTION_JS = r"""
c => {
  const ctx = c.getContext('2d'); if (!ctx) return {dx:0,dy:0,n:0};
  const w=c.width, h=c.height, cur=ctx.getImageData(0,0,w,h).data, bef=window.__latheBefore;
  if (!bef) return {dx:0,dy:0,n:0};
  const br=cur[0], bg=cur[1], bb=cur[2];
  let fx=0,fy=0,fn=0, tx=0,ty=0,tn=0;
  for (let y=0; y<h; y+=3){ for (let x=0; x<w; x+=3){ const i=(y*w+x)*4;
    const chg = Math.abs(cur[i]-bef[i])+Math.abs(cur[i+1]-bef[i+1])+Math.abs(cur[i+2]-bef[i+2]);
    if (chg > 60){                                            // this pixel is part of something that moved
      if (Math.abs(bef[i]-br)+Math.abs(bef[i+1]-bg)+Math.abs(bef[i+2]-bb) > 60){ fx+=x; fy+=y; fn++; }  // FROM
      if (Math.abs(cur[i]-br)+Math.abs(cur[i+1]-bg)+Math.abs(cur[i+2]-bb) > 60){ tx+=x; ty+=y; tn++; }  // TO
    } } }
  if (fn===0 || tn===0) return {dx:0,dy:0,n:fn+tn};
  return {dx: tx/tn - fx/fn, dy: ty/tn - fy/fn, n: Math.min(fn,tn)};
}
"""

# JS reading a selector's text (null if the element is absent) and the whole visible body text.
_SEL_TEXT_JS = "s => { const e = document.querySelector(s); return e ? (e.textContent || '') : null; }"
_BODY_TEXT_JS = "() => document.body ? (document.body.innerText || '') : ''"


def build_script(behavior):
    """Compile a DATA behavioral spec into a trusted Playwright gate script (string). Raises on bad DATA."""
    trials = _validate(behavior)
    return (
        "import os, re\n"
        "from playwright.sync_api import sync_playwright\n"
        "path = os.environ['ARTIFACT_FILE']\n"
        "url = 'file:///' + path.replace(os.sep, '/')\n"
        "TRIALS = " + repr(trials) + "\n"   # Python literal (trials contain None) — NOT json (json emits `null`)
        "MIN_FRAC = " + repr(MIN_FRAC) + "\n"
        "CENTROID = " + json.dumps(_CENTROID_JS) + "\n"
        "STASH = " + json.dumps(_STASH_JS) + "\n"
        "MOTION = " + json.dumps(_MOTION_JS) + "\n"
        "SEL_TEXT = " + json.dumps(_SEL_TEXT_JS) + "\n"
        "BODY_TEXT = " + json.dumps(_BODY_TEXT_JS) + "\n"
        "def _num(s):\n"
        "    m = re.search(r'-?\\d+(?:\\.\\d+)?', s or '')\n"
        "    return float(m.group()) if m else None\n"
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
        "        need_canvas = t['expect'] is not None\n"
        "        c0 = None\n"
        "        if need_canvas:\n"
        "            try:\n"
        "                c0 = page.eval_on_selector('canvas', CENTROID)\n"
        "            except Exception as e:\n"
        "                fails.append('no canvas: ' + str(e)[:80]); page.close(); continue\n"
        "            if not c0 or c0['n'] == 0:\n"
        "                fails.append(repr(t) + ' -> canvas is blank before the drive'); page.close(); continue\n"
        "        st = t['state']\n"
        "        s0 = page.evaluate(SEL_TEXT, st['selector']) if (st and st['kind'] == 'selector') else None\n"
        "        if st and st['kind'] == 'selector' and s0 is None:\n"
        "            fails.append(repr(t) + ' -> state selector %r not found on the page' % st['selector']); page.close(); continue\n"
        "        if need_canvas:\n"
        "            try: page.evaluate(STASH)          # snapshot the canvas right before the drive (for the motion measure)\n"
        "            except Exception: pass\n"
        "        v = t['verb']\n"
        "        if v == 'hold':\n"
        "            page.keyboard.down(t['key']); page.wait_for_timeout(t['ms']); page.keyboard.up(t['key'])\n"
        "        elif v == 'press':\n"
        "            page.keyboard.press(t['key']); page.wait_for_timeout(t['ms'])\n"
        "        elif v == 'click':\n"
        "            page.mouse.click(t['x'], t['y']); page.wait_for_timeout(t['ms'])\n"
        "        else:\n"
        "            page.wait_for_timeout(t['ms'])   # idle\n"
        "        if errors:\n"
        "            fails.append(repr(t) + ' -> JS error: ' + ' | '.join(errors[:2]))\n"
        "        if need_canvas:\n"
        "            c1 = page.eval_on_selector('canvas', CENTROID)\n"
        "            if not c1 or c1['n'] == 0:\n"
        "                fails.append(repr(t) + ' -> foreground vanished after the drive (blank canvas)'); page.close(); continue\n"
        "            dx = c1['x'] - c0['x']; dy = c1['y'] - c0['y']\n"
        "            tx = MIN_FRAC * c0['w']; ty = MIN_FRAC * c0['h']\n"
        "            try: mo = page.eval_on_selector('canvas', MOTION)\n"      # displacement of ONLY the moving element(s)
        "            except Exception: mo = {'dx':0,'dy':0,'n':0}\n"
        "            mn = mo.get('n',0); mdx = mo.get('dx',0); mdy = mo.get('dy',0)\n"
        "            MMIN = 8   # need a few changed sample-pixels for the motion signal to count (else it's noise)\n"
        "            exp = t['expect']; ok = True; why = ''\n"
        # A direction passes if EITHER the whole-scene centroid OR the moving-element motion clears the bar in
        # that direction. Additive: nothing that passed before fails now; games with big static scenery (paddle
        # games) that the whole-scene measure could never satisfy now pass on the controlled element's motion.
        "            if exp == 'up':      ok = (dy < -ty) or (mn>=MMIN and mdy < -ty); why = 'expected UP (scene dy=%.1f, moving-part dy=%.1f, need<%.1f)' % (dy, mdy, -ty)\n"
        "            elif exp == 'down':  ok = (dy >  ty) or (mn>=MMIN and mdy >  ty); why = 'expected DOWN (scene dy=%.1f, moving-part dy=%.1f, need>%.1f)' % (dy, mdy, ty)\n"
        "            elif exp == 'left':  ok = (dx < -tx) or (mn>=MMIN and mdx < -tx); why = 'expected LEFT (scene dx=%.1f, moving-part dx=%.1f, need<%.1f)' % (dx, mdx, -tx)\n"
        "            elif exp == 'right': ok = (dx >  tx) or (mn>=MMIN and mdx >  tx); why = 'expected RIGHT (scene dx=%.1f, moving-part dx=%.1f, need>%.1f)' % (dx, mdx, tx)\n"
        "            elif exp == 'move':  ok = (abs(dx) > tx or abs(dy) > ty) or (mn>=MMIN and (abs(mdx)>tx or abs(mdy)>ty)); why = 'expected motion (scene dx=%.1f dy=%.1f, moving-part dx=%.1f dy=%.1f)' % (dx, dy, mdx, mdy)\n"
        "            elif exp == 'still': ok = (abs(dx) <= tx and abs(dy) <= ty); why = 'expected NO motion (dx=%.1f dy=%.1f)' % (dx, dy)\n"
        "            if not ok:\n"
        "                fails.append(repr(t) + ' -> ' + why)\n"
        "        if st:\n"
        "            if st['kind'] == 'selector':\n"
        "                s1 = page.evaluate(SEL_TEXT, st['selector'])\n"
        "                op = st['op']\n"
        "                if op == 'changes' and (s1 or '') == (s0 or ''):\n"
        "                    fails.append(repr(t) + ' -> state %r did not change (%r) after the drive' % (st['selector'], s0))\n"
        "                elif op == 'stable' and (s1 or '') != (s0 or ''):\n"
        "                    fails.append(repr(t) + ' -> state %r changed %r->%r but was expected STABLE' % (st['selector'], s0, s1))\n"
        "                elif op == 'increases':\n"
        "                    n0, n1 = _num(s0), _num(s1)\n"
        "                    if n0 is None or n1 is None or not (n1 > n0):\n"
        "                        fails.append(repr(t) + ' -> state %r did not INCREASE (%r->%r)' % (st['selector'], s0, s1))\n"
        "            else:\n"
        "                body = (page.evaluate(BODY_TEXT) or '').lower()\n"
        "                needle = st['text'].lower()\n"
        "                if st['kind'] == 'text_absent' and needle in body:\n"
        "                    fails.append(repr(t) + ' -> forbidden text %r appeared (e.g. instant game-over)' % st['text'])\n"
        "                elif st['kind'] == 'text_present' and needle not in body:\n"
        "                    fails.append(repr(t) + ' -> required text %r was not present' % st['text'])\n"
        "        page.close()\n"
        "    browser.close()\n"
        "assert not fails, 'BEHAVIORAL FAIL: ' + ' ;; '.join(fails)\n"
        "print('BEHAVIORAL PASS: %d trial(s) — inputs produce the specified foreground/state response' % len(TRIALS))\n"
    )
